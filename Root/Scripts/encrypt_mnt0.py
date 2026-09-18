import sys, zlib, struct, hashlib
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

BODY_OFFSET = 100
CIPHERTEXT_OFFSET = 0x12C
HEADER_LEN = 0x28
MAGIC = 0x23311200
VERSION = 0

KEY_HEX = "YOUR_PRIVATE_KEY_HERE"
IV_HEX  = "AND_THE_IV_HERE"
key, iv = bytes.fromhex(KEY_HEX), bytes.fromhex(IV_HEX)

if len(sys.argv) != 4:
    print("usage: python encrypt_mnt0.py <original_file> <edited_configuration.xml> <output_file>")
    sys.exit(1)

template_path, xml_path, out_path = sys.argv[1], sys.argv[2], sys.argv[3]
template = open(template_path, "rb").read()
xml = open(xml_path, "rb").read()
compressed = zlib.compress(xml, 9)
complen = len(compressed)
origlen = len(xml)
crc = zlib.crc32(compressed) & 0xffffffff

header = struct.pack("<I", MAGIC) + struct.pack(">I", complen) + struct.pack(">I", crc) \
         + struct.pack(">I", origlen) + struct.pack(">I", VERSION)

reserved = b"\x00" * (HEADER_LEN - len(header))

plaintext_body = header + reserved + compressed
padded = pad(plaintext_body, 16)
ciphertext = AES.new(key, AES.MODE_CBC, iv).encrypt(padded)
prefix = template[32:CIPHERTEXT_OFFSET]
body = prefix + ciphertext
full_from_100 = template[BODY_OFFSET:CIPHERTEXT_OFFSET] + ciphertext
digest = hashlib.sha256(full_from_100).digest()
out = digest + template[32:BODY_OFFSET] + full_from_100
assert len(out) == 32 + (BODY_OFFSET - 32) + len(full_from_100)
open(out_path, "wb").write(out)
