import base64
import sys
import time
from Crypto.Cipher import AES

KEY_HEX = "YOUR_PRIVATE_KEY_HERE"
IV_HEX  = "AND_YOUR_IV_HERE"

class GlibcRand:
    def __init__(self, seed):
        if seed == 0:
            seed = 1
        self.state = [0] * 31
        self.state[0] = seed
        for i in range(1, 31):
            hi = self.state[i - 1] // 127773
            lo = self.state[i - 1] % 127773
            self.state[i] = 16807 * lo - 2836 * hi
            if self.state[i] < 0:
                self.state[i] += 2147483647

        self.fptr = 3
        self.rptr = 0

        for _ in range(310):
            self.rand()

    def rand(self):
        u_fptr = self.state[self.fptr] & 0xFFFFFFFF
        u_rptr = self.state[self.rptr] & 0xFFFFFFFF

        val = (u_fptr + u_rptr) & 0xFFFFFFFF

        if val >= 2147483648:
            self.state[self.fptr] = val - 4294967296
        else:
            self.state[self.fptr] = val

        self.fptr = (self.fptr + 1) % 31
        self.rptr = (self.rptr + 1) % 31

        return val >> 1

def decrypt_cookie(b64_cookie):
    key = bytes.fromhex(KEY_HEX)
    iv = bytes.fromhex(IV_HEX)
    ciphertext = base64.b64decode(b64_cookie)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    plaintext = cipher.decrypt(ciphertext)
    return plaintext[:32].decode('ascii')

def brute_force_timestamp(target_token):
    target_vals = [int(target_token[i*8:(i+1)*8], 16) for i in range(4)]
    current_time = int(time.time())
    start_time = current_time - 86400

    for t in range(current_time, start_time - 1, -1):
        r = GlibcRand(t)
        vals = [r.rand() for _ in range(4)]
        if vals == target_vals:
            return t

    return None

def main():
    if len(sys.argv) != 2:
        print(f"Usage: python {sys.argv[0]} <base64_cookie>")
        sys.exit(1)

    b64_cookie = sys.argv[1]

    token = decrypt_cookie(b64_cookie)
    print(f"token: {token}")

    found_t = brute_force_timestamp(token)
    if found_t:
        print(f"timestamp: {found_t}")
    else:
        print("timestamp: not found in the last 24 hours")

if __name__ == "__main__":
    main()
