import sys, zlib, struct, hashlib
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

BODY_OFFSET = 100
CIPHERTEXT_OFFSET = 0x12C

KEY_HEX = "YOUR_PRIVATE_KEY_HERE"
IV_HEX  = "AND_THE_IV_HERE"

key, iv = bytes.fromhex(KEY_HEX), bytes.fromhex(IV_HEX)

path = sys.argv[1]
data = open(path, "rb").read()

digest_stored = data[0:32]
digest_calc = hashlib.sha256(data[BODY_OFFSET:]).digest()
print("digest match:", digest_calc == digest_stored)

ct = data[CIPHERTEXT_OFFSET:]
ct = ct[: (len(ct) // 16) * 16]

pt = AES.new(key, AES.MODE_CBC, iv).decrypt(ct)
try:
    pt = unpad(pt, 16)
except ValueError:
    pass

magic       = struct.unpack_from("<I", pt, 0x00)[0]
complen     = struct.unpack_from(">I", pt, 0x04)[0]
crc_stored  = struct.unpack_from(">I", pt, 0x08)[0]
origlen     = struct.unpack_from(">I", pt, 0x0C)[0]
version     = struct.unpack_from(">I", pt, 0x10)[0]

print(f"magic=0x{magic:08x} complen={complen} crc={crc_stored:08x} origlen={origlen} version={version}")

compressed = pt[0x28 : 0x28 + complen]
crc_calc = zlib.crc32(compressed) & 0xffffffff
print("crc match:", crc_calc == crc_stored)

try:
    xml = zlib.decompress(compressed)
except zlib.error:
    xml = zlib.decompress(compressed, -15)

assert len(xml) == origlen or len(xml) == origlen - 1
open("configuration.xml", "wb").write(xml)
