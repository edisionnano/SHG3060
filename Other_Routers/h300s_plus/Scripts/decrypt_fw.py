import sys
import hashlib
from Crypto.Cipher import AES

ALPHABET = "26aejsw37bfktx48chmuy59dipvz"
SALT1 = b"83f323b7132703029da5f4a9daa72a60"
SALT2 = b"b7293e8150d1330c6c3d93f2fa81331b"
HEADER_SIZE = 0xA0

def md5(*parts: bytes) -> bytes:
    h = hashlib.md5()
    for p in parts:
        h.update(p)
    return h.digest()

def sercomm_hexdigest(digest: bytes) -> bytes:
    out = bytearray()
    for c in digest:
        c_hex = format(c, "02x").encode()
        if c_hex.startswith(b"0"):
            out += c_hex[1:]
            out += b"\x00"
        else:
            out += c_hex
    return bytes(out)

def permute(hex_bytes: bytes) -> bytes:
    out = bytearray(hex_bytes)
    for i in range(len(out)):
        out[i] = ord(ALPHABET[out[i] % 28])
    return bytes(out)

def unnullpad(b: bytes) -> bytes:
    return b.split(b"\x00")[0]

def parse_header(header: bytes):
    fw_version = unnullpad(header[0x20:0x40])
    iv32 = header[0x40:0x60]
    nullpad2 = header[0x60:0x80]
    filesize = int(unnullpad(header[0x80:0xA0]) or b"0")
    return {
        "fw_version": fw_version,
        "iv16": iv32[:16],
        "nullpad2": nullpad2,
        "filesize": filesize,
    }

def derive_key(fw_version: bytes, nullpad2: bytes) -> bytes:
    d1 = md5(nullpad2, fw_version)
    d2 = md5(SALT2, fw_version)
    d3 = md5(SALT1, fw_version)
    final = md5(d1, d2, d3)
    return permute(sercomm_hexdigest(final))

def decrypt_ota(data: bytes) -> bytes:
    fields = parse_header(data[:HEADER_SIZE])
    ciphertext = data[HEADER_SIZE:]
    key = derive_key(fields["fw_version"], fields["nullpad2"])
    cipher = AES.new(key, AES.MODE_CBC, fields["iv16"])
    plaintext = cipher.decrypt(ciphertext)
    if 0 < fields["filesize"] <= len(plaintext):
        plaintext = plaintext[: fields["filesize"]]
    return plaintext

def main():
    if len(sys.argv) != 3:
        sys.exit(1)
    in_path, out_prefix = sys.argv[1], sys.argv[2]
    data = open(in_path, "rb").read()
    plaintext = decrypt_ota(data)
    with open(out_prefix, "wb") as f:
        f.write(plaintext)

if __name__ == "__main__":
    main()
