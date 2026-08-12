from Crypto.Cipher import AES

key = b'jErRy' + b'\x00' * 27
iv  = b'\x83' * 16

with open('default.xml', 'rb') as f:
    data = f.read()

cipher = AES.new(key, AES.MODE_CBC, iv)
plaintext = cipher.decrypt(data)
pad_len = plaintext[-1]
plaintext = plaintext[:-pad_len]

with open('default_decrypted.xml', 'wb') as f:
    f.write(plaintext)
