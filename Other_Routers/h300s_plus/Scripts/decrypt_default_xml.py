import gzip, hashlib, os, sys
from Crypto.Cipher import AES

ALPHABET = "26aejsw37bfktx48chmuy59dipvz"
SALT1 = b"83f323b7132703029da5f4a9daa72a60"
SALT2 = b"48b526aa1f0552bf3e67f94a9afd3b45"
FDATA = b"b7293e8150d1330c6c3d93f2fa81331b"
IV = b"\x83" * 16


def md5(*chunks):
    h = hashlib.md5()
    for c in chunks:
        h.update(c)
    return h.digest()


def derive_key(fw_version):
    digest = md5(md5(FDATA, fw_version), md5(SALT1, fw_version), md5(SALT2, fw_version))
    expanded = b"".join(
        format(b, "02x")[1:].encode() + b"\x00" if b < 16 else format(b, "02x").encode()
        for b in digest
    )
    return bytes(ord(ALPHABET[b % 28]) for b in expanded)


def decrypt(data, fw_version):
    pt = AES.new(derive_key(fw_version), AES.MODE_CBC, IV).decrypt(data)
    pad = pt[-1]
    if 1 <= pad <= 16 and pt[-pad:] == bytes([pad]) * pad:
        pt = pt[:-pad]
    return gzip.decompress(pt) if pt[:2] == b"\x1f\x8b" else pt


def main():
    fw_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fw_version")
    with open(fw_path, "rb") as f:
        fw_version = f.read().strip()
    with open(sys.argv[1], "rb") as f:
        data = f.read()
    with open(sys.argv[2], "wb") as f:
        f.write(decrypt(data, fw_version))


if __name__ == "__main__":
    main()
