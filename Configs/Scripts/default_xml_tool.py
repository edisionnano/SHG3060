import struct
import hashlib
import argparse
from pathlib import Path
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes


def descramble(ki):
    scr = bytearray(96)
    for i in range(24):
        d = (24 - i) if (i & 1) else i
        scr[d*4:d*4+4] = ki[i*4:i*4+4]
    return bytes(scr)


def derive_key_iv(scr):
    key = hashlib.md5(scr[0:32]).digest() + hashlib.md5(scr[64:96]).digest()
    iv = scr[32:48]
    return key, iv


def pkcs7_pad(data, block_size=16):
    pad_len = block_size - (len(data) % block_size)
    return data + bytes([pad_len]) * pad_len


def pkcs7_unpad(data):
    return data[:-data[-1]]


def cmd_decode(cfg_path):
    out_dir = Path('decoded')
    out_dir.mkdir(exist_ok=True)

    data = Path(cfg_path).read_bytes()

    reserved = data[64:100]
    key_blob = data[100:196]
    zero_pad = data[196:300]
    ciphertext = data[300:]

    scr = descramble(key_blob)
    key, iv = derive_key_iv(scr)

    dec = Cipher(algorithms.AES(key), modes.CBC(iv)).decryptor()
    pt = dec.update(ciphertext) + dec.finalize()
    plaintext = pkcs7_unpad(pt)

    (out_dir / 'reserved.bin').write_bytes(reserved)
    (out_dir / 'key_blob.bin').write_bytes(key_blob)
    (out_dir / 'zero_pad.bin').write_bytes(zero_pad)
    (out_dir / 'configuration.xml').write_bytes(plaintext)

    print(f"Decoded '{cfg_path}' -> {out_dir}/")
    print(f"  configuration.xml : {len(plaintext)} bytes (edit this)")
    print(f"  key_blob.bin      : static per-firmware key material (leave untouched)")
    print(f"  reserved.bin, zero_pad.bin : static padding (leave untouched)")


def cmd_encode(out_name):
    in_dir = Path('decoded')
    out_dir = Path('encoded')
    out_dir.mkdir(exist_ok=True)

    reserved = (in_dir / 'reserved.bin').read_bytes()
    key_blob = (in_dir / 'key_blob.bin').read_bytes()
    zero_pad = (in_dir / 'zero_pad.bin').read_bytes()
    plaintext = (in_dir / 'configuration.xml').read_bytes()

    scr = descramble(key_blob)
    key, iv = derive_key_iv(scr)

    padded = pkcs7_pad(plaintext)
    enc = Cipher(algorithms.AES(key), modes.CBC(iv)).encryptor()
    ciphertext = enc.update(padded) + enc.finalize()

    payload = key_blob + zero_pad + ciphertext
    digest = hashlib.sha256(payload).digest()
    signature = digest + b'\x00' * 32

    final = signature + reserved + payload

    out_file = out_dir / out_name
    out_file.write_bytes(final)

    print(f"Encoded -> {out_file} ({len(final)} bytes)")
    print(f"  plaintext size : {len(plaintext)} bytes")
    print(f"  padded size    : {len(padded)} bytes")
    print(f"  ciphertext size: {len(ciphertext)} bytes")

    check = out_file.read_bytes()
    check_sig = hashlib.sha256(check[100:]).digest()
    print(f"  signature self-check: {'OK' if check_sig == check[0:32] else 'MISMATCH'}")


def main():
    parser = argparse.ArgumentParser(description="Decode / encode router default.xml config files")
    parser.add_argument('command', choices=['decode', 'encode'])
    parser.add_argument('--cfg', default='default.xml',
                         help="path to encrypted file to decode, or output filename to write when encoding")
    args = parser.parse_args()

    if args.command == 'decode':
        cmd_decode(args.cfg)
    else:
        cmd_encode(args.cfg)


if __name__ == '__main__':
    main()
