import hashlib
import sys

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

MAGIC = b"V0daf0n5_123@hybR1D@ccesshyf1234"


def atol(field):
    s = field.split(b"\x00", 1)[0].lstrip()
    i = 1 if s[:1] in (b"+", b"-") else 0
    j = i
    while j < len(s) and s[j:j + 1].isdigit():
        j += 1
    return int(s[:j] or b"0")


def decrypt_image(blob):
    f0, f1, f2, f3, f4 = (blob[i:i + 32] for i in range(0, 160, 32))
    key = bytes(a ^ b for a, b in zip(
        hashlib.md5(f3 + f1).digest() + hashlib.md5(f4 + f1).digest(), MAGIC))
    dec = Cipher(algorithms.AES(key), modes.CBC(f2[:16])).decryptor()
    pt = dec.update(blob[160:]) + dec.finalize()
    length = atol(f4)
    return pt[:length] if 0 <= length <= len(pt) else pt


if __name__ == "__main__":
    with open(sys.argv[1], "rb") as fh:
        blob = fh.read()
    with open(sys.argv[2], "wb") as fh:
        fh.write(decrypt_image(blob))
