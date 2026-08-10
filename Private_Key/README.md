# The Private and Public Keys
Each SHG3060 has a unique private key used to encrypt a lot of things including the configuration exported from the web interface. Unlike the default WiFi and web interface passwords, the private key is not burned into the nvram at the factory but rather derived by an algorithm that exists locally in the router's software. The public key is then used to encrypt the first 48 bytes of the file that stores the private key.

## Analysis of the private key
The private key and IV are stored at `/mnt/2/.p`, encrypted using the public key.<br>
On boot, `crypt_init_key` of `/lib/libsex_crypt.so` checks if the file exists. If the file exists then it checks if the file is corrupted (more on that later). If any of these checks fail the library will mint a new one using the following algorithm:
1. It calls `util_ramdom_str` (probably a typo?) of `/lib/libutility.so` providing it with an 8byte buffer and the number 7.
2. `util_ramdom_str` attempts to read 4 bytes from `/dev/urandom`, if that fails it gets the current timestamp.
3. That value is then used a seed to get a random string (a-z A-Z 0-9, locale is `C`, uses Glibc)
4. The second parameter tells `util_ramdom_str` how many bytes to read into the buffer, so the 8th byte is left 0 (at least on ARM)
5. `crypt_init_key` uses the buffer as salt and the word `secret` as the key and calls `EVP_BytesToKey` from OpenSSL to create the private key

## Decrypting /mnt/2/.p
In case we are able to retrieve files arbitrarily in the future, this will be very helpful.<br>
If we run `strings` on `/lib/libsex_crypt.so` we can see some strings that look like keys and if we trace their crossreferences they will point to `crypt_get_public_key`.<br>
Here is what it does:
1. It starts by checking our model, if it's the `Vodafone-H-500-s` it returns `9382D105FCB222798AD2B7F059A1476D` else if it's the `VD5244BV2` it returns `A356C31E0F4704DB0BE6FA354BB06970` and the IV is `4B73AC6597137894`
2. These strings are scrambled, to descramble them it calls a helper function that breaks them into 4 byte chunks
3. The chunks in even positions (0,2,4,etc.) stay as is
4. The odd positions (1,3,5,etc.) are placed in the opposite order. The new position is determined by doing chunk count minus current position. So if we have an array with 8 chunks, the second chunk (position 1) goes to position 8-1=7
5. `VD5244BV2` key becomes `A35669700F47FA350BE604DB4BB0C31E`, `Vodafone-H-500-s` key becomes `9382476DFCB2B7F08AD2227959A1D105` and the IV becomes `4B73AC6597137894`

Once you have the `.p` file you can run the script with the path as the sole argument to decrypt and verify it. The output will look like this
```
checksum stored:   3f9b67e982f74e4bdb31eccd103875b8
checksum computed: 3f9b67e982f74e4bdb31eccd103875b8
checksum match:    True
private key: 43ca9f52c0dd2488099728483c69efa9b35705eb7c492fe0e13965915b4d271b
private iv:  6a04d3c15a642608224abc26fb2a2953
```
The file layout of `.p` is as follows:<br>
Bytes 0-48 are the private key + iv encrypted<br>
Bytes 48-80 are the MD5 checksum<br>
Bytes 80-96 are padding

## Bruteforcing the private key
While the private key is 256 bits the only part of it we don't already know are the 32 bits it reads from `/dev/urandom`, that's only 2^32 possibilities to brute force (a bit less than 4.3 billion).<br>
The way the `configurationBackup.cfg` is created is as follows:
1. First it's compressed using zlib
2. It reads the 32 characters from the password provided in the interface. If it's more than 32 it gets the first 32, if it's less it's padded with zeroes
3. It computes the md5 hash of those 32 characters from the password and an md5 hash of the private key
4. Those hashes are joined to form a new AES256 key used to encrypt the file

So the decrypted file's first two bytes are the [zlib header](https://stackoverflow.com/questions/9050260/what-does-a-zlib-header-look-like)

Using this knowledge we can bruteforce the private key and IV.<br>
Compile the script `bruteforce_key.c` using this command:
```sh
gcc -O3 -march=native -o bruteforce_key bruteforce_key.c -lssl -lcrypto -lz
```
then run the exported binary `bruteforce_key` with the path to `configurationBackup.cfg` as an argument.<br>
It will ask you for the password you used to backup the file, I recommend something simple like `12345678`.<br>
Then it will occupy all CPU threads to find the key. On my Ryzen 5700X3D it took about 5 minutes.
Once it finishes, it will print the key and IV. Save them.
