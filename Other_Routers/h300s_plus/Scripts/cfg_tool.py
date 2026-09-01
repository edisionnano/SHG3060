import argparse
import hashlib
from pathlib import Path
from Crypto.Cipher import AES

ALPHABET = "26aejsw37bfktx48chmuy59dipvz"
IV = b"\x83" * 16
SALT1 = b"83f323b7132703029da5f4a9daa72a60"
SALT2 = b"48b526aa1f0552bf3e67f94a9afd3b45"
FDATA = b"b7293e8150d1330c6c3d93f2fa81331b"
SERCOMM_A = b"sErCoMm"
SERCOMM_B = b"eNtry3"
PRODUCT_CLASS = "W724VCi"
HEADER_KEYS = ["FW Version", "FW Description", "FW Create Time", "FW Group", "Board S/N"]
DECODED_DIR = Path("decoded")
ENCODED_DIR = Path("encoded")
PLAINTEXT_NAME = "config.xml"
HEADERS_NAME = "headers.txt"


def md5(*chunks):
    h = hashlib.md5()
    for c in chunks:
        h.update(c)
    return h.digest()


def _map_digest_to_alphabet(digest):
    tmp = bytearray(33)
    for i, v in enumerate(digest):
        s = f"{v:x}".encode("ascii")
        pos = 2 * i
        tmp[pos:pos + len(s)] = s
        if pos + len(s) < len(tmp):
            tmp[pos + len(s)] = 0
    return bytes(ord(ALPHABET[b % len(ALPHABET)]) for b in tmp[:32])


def derive_key_inner(product_class):
    c = product_class.encode("ascii") if product_class else b""
    d1 = md5(SERCOMM_A + SERCOMM_B)
    d2 = md5(SERCOMM_A + c)
    d3 = md5(SERCOMM_B + c)
    d4 = md5(d1 + d2 + d3)
    return _map_digest_to_alphabet(d4)


def derive_key_outer(password):
    if isinstance(password, str):
        password = password.encode()
    digest = md5(md5(FDATA, password), md5(SALT1, password), md5(SALT2, password))
    return _map_digest_to_alphabet(digest)


def pkcs7_pad(data, block=16):
    n = block - (len(data) % block)
    return data + bytes([n]) * n


def pkcs7_unpad(data):
    n = data[-1]
    if 1 <= n <= 16 and data[-n:] == bytes([n]) * n:
        return data[:-n]
    return data


def aes_cbc_decrypt(key, data):
    return AES.new(key, AES.MODE_CBC, IV).decrypt(data)


def aes_cbc_encrypt(key, data):
    return AES.new(key, AES.MODE_CBC, IV).encrypt(pkcs7_pad(data))


def hex_text_to_bytes(text):
    return bytes.fromhex("".join(text.split()))


def parse_header(raw):
    headers, pos = {}, 0
    for key in HEADER_KEYS:
        nl = raw.index(b"\n", pos)
        line = raw[pos:nl].decode("ascii", errors="replace").rstrip("\r")
        pos = nl + 1
        headers[key] = line[len(key) + 1:]
    return headers, raw[pos:]


def build_header(headers):
    return ("\n".join(f"{k}:{headers[k]}" for k in HEADER_KEYS) + "\n").encode("ascii")


def write_header_file(path, headers):
    path.write_text("\n".join(f"{k}:{v}" for k, v in headers.items()) + "\n")


def load_header_file(path):
    headers = {}
    for line in path.read_text().strip().splitlines():
        key, _, val = line.partition(":")
        headers[key.strip()] = val.strip()
    return headers


def cmd_decode(cfg_path, password=None):
    DECODED_DIR.mkdir(exist_ok=True)

    raw = Path(cfg_path).read_bytes()
    variant = 2 if password else 1

    if variant == 2:
        headers, body = parse_header(raw)
        pt = pkcs7_unpad(aes_cbc_decrypt(derive_key_outer(password), body))
        try:
            hex_text = pt.decode("ascii")
        except UnicodeDecodeError as e:
            raise SystemExit(f"Decryption failed, wrong password? ({e})")
        inner_bytes = hex_text_to_bytes(hex_text)
        key_inner = derive_key_inner("")
        write_header_file(DECODED_DIR / HEADERS_NAME, headers)
    else:
        inner_bytes = hex_text_to_bytes(raw.decode("ascii"))
        key_inner = derive_key_inner(PRODUCT_CLASS)

    plaintext = pkcs7_unpad(aes_cbc_decrypt(key_inner, inner_bytes))
    out_path = DECODED_DIR / PLAINTEXT_NAME
    out_path.write_bytes(plaintext)


def cmd_encode(password=None):
    ENCODED_DIR.mkdir(exist_ok=True)

    plaintext_path = DECODED_DIR / PLAINTEXT_NAME
    data = plaintext_path.read_bytes()
    if not data.endswith(b"\x00"):
        data += b"\x00"

    variant = 2 if password else 1
    key_inner = derive_key_inner("" if variant == 2 else PRODUCT_CLASS)
    ct_inner = aes_cbc_encrypt(key_inner, data)
    hex_text = ct_inner.hex().upper()

    if variant == 1:
        out_path = ENCODED_DIR / "config.hex"
        out_path.write_text(hex_text, encoding="ascii")
        return

    headers_path = DECODED_DIR / HEADERS_NAME
    headers = load_header_file(headers_path)

    outer_ct = aes_cbc_encrypt(derive_key_outer(password), (hex_text + "\n").encode("ascii"))
    final = build_header(headers) + outer_ct
    out_path = ENCODED_DIR / "Speedport_Plus_Mod.config"
    out_path.write_bytes(final)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="command", required=True)

    d = sub.add_parser("decode")
    d.add_argument("--cfg", required=True, type=Path)
    d.add_argument("--password")

    e = sub.add_parser("encode")
    e.add_argument("--password")

    args = ap.parse_args()

    if args.command == "decode":
        cmd_decode(args.cfg, password=args.password)
    else:
        cmd_encode(password=args.password)


if __name__ == "__main__":
    main()
