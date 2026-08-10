import os
import re
import struct
import zlib
import hashlib
import base64
import textwrap
import subprocess
import tempfile
import argparse
import configparser
from pathlib import Path
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

CONFIG_PATH = Path("config.ini")

DEFAULTS = {
    "keys": {
        "private_key": "YOUR_PRIVATE_KEY_HERE",
        "private_iv":  "AND_THE_IV_HERE",
        "password":    "CFG_PASSWORD_HERE",
    },
}


def load_config():
    cfg = configparser.ConfigParser()
    if not CONFIG_PATH.exists():
        cfg.read_dict(DEFAULTS)
        with open(CONFIG_PATH, "w") as f:
            cfg.write(f)
    else:
        cfg.read(CONFIG_PATH)
    return cfg


CFG = load_config()
PRIVATE_KEY = bytes.fromhex(CFG["keys"]["private_key"])
PRIVATE_IV  = bytes.fromhex(CFG["keys"]["private_iv"])
PASSWORD    = CFG["keys"].get("password", "")

PFX_PATH    = "config.pfx"
PFX_PASS    = "VD5244BV2"
CONFXML_CIPHERTEXT_OFFSET = 0x12C
HEADER_SIZE = 0x4B8

HEADER_KEYS = ["FW Version", "FW Description", "FW Create Time", "FW Group", "Board S/N"]


def derive_cfg_key(password_str):
    handle32 = password_str.encode()[:32].ljust(32, b'\x00')
    handle_md5 = hashlib.md5(handle32).digest()
    key_part2 = hashlib.md5(PRIVATE_KEY).digest()
    return handle_md5 + key_part2


def get_password():
    return PASSWORD


def aes_cbc_decrypt(key, iv, ciphertext):
    ct = ciphertext[: (len(ciphertext) // 16) * 16]
    return AES.new(key, AES.MODE_CBC, iv).decrypt(ct)


def aes_cbc_encrypt(key, iv, plaintext):
    return AES.new(key, AES.MODE_CBC, iv).encrypt(pad(plaintext, 16))


def util_crc32(data):
    return struct.pack('<I', zlib.crc32(data) & 0xFFFFFFFF)


def decode_confxml(blob):
    pt = aes_cbc_decrypt(PRIVATE_KEY, PRIVATE_IV, blob[CONFXML_CIPHERTEXT_OFFSET:])
    try:
        return unpad(pt, 16)
    except ValueError:
        return pt


def encode_confxml(xml_bytes):
    pt = xml_bytes if xml_bytes.endswith(b'\x00') else xml_bytes + b'\x00'
    ct = aes_cbc_encrypt(PRIVATE_KEY, PRIVATE_IV, pt)
    ptr_buffer = b'\x00' * 200 + ct
    sig64 = hashlib.sha256(ptr_buffer).digest() + b'\x00' * 32
    return sig64 + b'\x00' * 36 + ptr_buffer


def parse_payload(data):
    raw_header = data[:HEADER_SIZE]
    hw_id = raw_header[:32].split(b'\x00')[0].decode('utf-8', errors='ignore')
    fw_group = raw_header[1184:1200].split(b'\x00')[0].decode('utf-8', errors='ignore')
    conf_size = struct.unpack('<I', raw_header[1200:1204])[0]
    log_size = struct.unpack('<I', raw_header[1204:1208])[0]
    log_start = HEADER_SIZE
    log_end = log_start + log_size
    conf_end = log_end + conf_size
    return {
        'header_raw': raw_header,
        'hw_id': hw_id,
        'fw_group': fw_group,
        'conf_size': conf_size,
        'log_size': log_size,
        'crc_bytes': data[-4:],
        'call_log': data[log_start:log_end],
        'confxml': data[log_end:conf_end],
    }


def build_payload(header_raw, call_log, confxml_bin):
    body = call_log + confxml_bin
    return header_raw + body + util_crc32(body)


def pkcs7_extract_content(der):
    with tempfile.NamedTemporaryFile(suffix='.der', delete=False) as f_in:
        f_in.write(der)
        in_path = f_in.name
    out_path = tempfile.mktemp(suffix='.bin')

    for subcmd in ('smime', 'cms'):
        r = subprocess.run(
            ['openssl', subcmd, '-verify', '-noverify',
             '-inform', 'DER', '-in', in_path, '-out', out_path],
            capture_output=True
        )
        if r.returncode == 0:
            break

    os.unlink(in_path)
    content = Path(out_path).read_bytes()
    os.unlink(out_path)
    return content


def _pkcs12_extract(extra_args):
    out_path = tempfile.mktemp(suffix='.pem')
    base = ['openssl', 'pkcs12', '-in', PFX_PATH, *extra_args,
            '-out', out_path, '-passin', f'pass:{PFX_PASS}']
    r = subprocess.run(base, capture_output=True)
    if r.returncode != 0:
        subprocess.run(base + ['-legacy'], capture_output=True)
    return out_path


def pkcs7_sign_content(raw_payload):
    with tempfile.NamedTemporaryFile(delete=False, suffix='.bin') as f:
        f.write(raw_payload)
        content_path = f.name

    cert_path = _pkcs12_extract(['-clcerts', '-nokeys'])
    key_path = _pkcs12_extract(['-nocerts', '-nodes'])
    chain_path = _pkcs12_extract(['-cacerts', '-nokeys'])
    has_chain = os.path.getsize(chain_path) > 0
    out_path = tempfile.mktemp(suffix='.der')

    cmd = ['openssl', 'cms', '-sign', '-in', content_path, '-signer', cert_path,
           '-inkey', key_path, '-outform', 'DER', '-out', out_path,
           '-binary', '-nosmimecap', '-nodetach']
    if has_chain:
        cmd += ['-certfile', chain_path]
    subprocess.run(cmd, capture_output=True)

    der = Path(out_path).read_bytes()
    for p in (content_path, cert_path, key_path, chain_path, out_path):
        os.unlink(p)

    b64 = '\n'.join(textwrap.wrap(base64.b64encode(der).decode('ascii'), 64))
    return b64.encode('ascii')


def parse_cfg_headers(raw):
    headers = {}
    pos = 0
    for key in HEADER_KEYS:
        nl = raw.index(b'\n', pos)
        line = raw[pos:nl].decode('utf-8', errors='replace').rstrip('\r')
        pos = nl + 1
        headers[key] = line[len(key) + 1:]
    return headers, raw[pos:]


def build_cfg_text_header(headers):
    return ('\n'.join(f"{k}:{headers[k]}" for k in HEADER_KEYS) + '\n').encode('ascii')


def cfg_decrypt_payload(content, cfg_key):
    declared_len = struct.unpack('<I', content[:4])[0]
    return declared_len, aes_cbc_decrypt(cfg_key, PRIVATE_IV, content[4:])


def cfg_encrypt_payload(compressed, declared_len, cfg_key):
    return struct.pack('<I', declared_len) + aes_cbc_encrypt(cfg_key, PRIVATE_IV, compressed)


def cmd_decode(cfg_path):
    out_dir = Path('decoded')
    out_dir.mkdir(exist_ok=True)

    cfg_key = derive_cfg_key(get_password())

    raw = Path(cfg_path).read_bytes()
    headers, b64_body = parse_cfg_headers(raw)
    (out_dir / 'cfg_header.txt').write_text(
        '\n'.join(f"{k}:{v}" for k, v in headers.items()) + '\n'
    )

    b64_clean = re.sub(rb'\s+', b'', b64_body)
    b64_clean += b'=' * ((4 - len(b64_clean) % 4) % 4)
    der = base64.b64decode(b64_clean)

    content = pkcs7_extract_content(der)
    declared_len, compressed = cfg_decrypt_payload(content, cfg_key)
    data = zlib.decompress(compressed)
    p = parse_payload(data)

    (out_dir / 'header.bin').write_bytes(p['header_raw'])
    if p['log_size'] > 0:
        (out_dir / 'call_log.log.csv').write_bytes(p['call_log'])
    (out_dir / 'confxml.bin').write_bytes(p['confxml'])
    (out_dir / 'configuration.xml').write_bytes(decode_confxml(p['confxml']))
    (out_dir / 'declared_len.txt').write_text(str(declared_len))


def cmd_encode(cfg_path):
    in_dir = Path('decoded')
    out_dir = Path('encoded')
    out_dir.mkdir(exist_ok=True)

    cfg_key = derive_cfg_key(get_password())

    header_raw = (in_dir / 'header.bin').read_bytes()
    xml_bytes = (in_dir / 'configuration.xml').read_bytes()
    call_log_path = in_dir / 'call_log.log.csv'
    call_log = call_log_path.read_bytes() if call_log_path.exists() else b''

    headers = {}
    for line in (in_dir / 'cfg_header.txt').read_text().strip().splitlines():
        key, _, val = line.partition(':')
        headers[key.strip()] = val.strip()

    confxml_bin = encode_confxml(xml_bytes)
    hdr = bytearray(header_raw)
    struct.pack_into('<I', hdr, 1200, len(confxml_bin))
    struct.pack_into('<I', hdr, 1204, len(call_log))
    header_raw = bytes(hdr)

    payload = build_payload(header_raw, call_log, confxml_bin)
    declared_len = len(payload)
    compressed = zlib.compress(payload)
    encrypted_content = cfg_encrypt_payload(compressed, declared_len, cfg_key)
    b64_body = pkcs7_sign_content(encrypted_content)

    final = build_cfg_text_header(headers) + b64_body + b'\n'
    (out_dir / 'configurationBackup_new.cfg').write_bytes(final)


def main():
    parser = argparse.ArgumentParser(description="Decode / encode configurationBackup.cfg files")
    parser.add_argument('command', choices=['decode', 'encode'])
    parser.add_argument('--cfg', default='configurationBackup.cfg')
    args = parser.parse_args()

    if args.command == 'decode':
        cmd_decode(args.cfg)
    else:
        cmd_encode(args.cfg)


if __name__ == '__main__':
    main()
