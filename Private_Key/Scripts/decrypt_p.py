import sys
import hashlib
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

PUBLIC_KEY = b"A356C31E0F4704DB0BE6FA354BB06970"
PUBLIC_IV  = b"4B73AC6597137894"


def permute_words(data: bytes) -> bytes:
    assert len(data) % 4 == 0
    n = len(data) // 4
    words = [data[i * 4:(i + 1) * 4] for i in range(n)]
    out = [None] * n
    for i in range(n):
        if i % 2 == 0:
            out[i] = words[i]
        else:
            out[n - i] = words[i]
    return b"".join(out)


def unwrap_p(path: str):
    with open(path, "rb") as f:
        data = f.read()

    ciphertext = data[0x00:0x30]
    stored_md5_hex = data[0x30:0x50].decode("ascii", errors="replace").rstrip("\x00")

    wrap_key = permute_words(PUBLIC_KEY)
    wrap_iv = permute_words(PUBLIC_IV)

    dec = Cipher(algorithms.AES(wrap_key), modes.CBC(wrap_iv)).decryptor()
    plaintext48 = dec.update(ciphertext) + dec.finalize()

    computed_md5_hex = hashlib.md5(plaintext48).hexdigest()
    ok = computed_md5_hex == stored_md5_hex

    private_key = plaintext48[:32]
    private_iv = plaintext48[32:48]

    return {
        "ok": ok,
        "stored_md5": stored_md5_hex,
        "computed_md5": computed_md5_hex,
        "private_key": private_key,
        "private_iv": private_iv,
    }


if __name__ == "__main__":
    path = sys.argv[1]
    result = unwrap_p(path)

    print(f"checksum stored: {result['stored_md5']}")
    print(f"checksum computed: {result['computed_md5']}")
    print(f"checksum match: {result['ok']}")
    print(f"private key: {result['private_key'].hex()}")
    print(f"private iv: {result['private_iv'].hex()}")
