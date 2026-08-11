# Firmware Analysis
This section will focus on decrypting OTA firmware packages and emulating them through QEMU. A big selection of those files can be found [here](https://github.com/k-marios/Gr_ISP_Router_Firmware/tree/main/Vodafone/Retail/Sercomm/Power_Station_WiFi6). `XS6_4200_12_all.img` is the latest version at the moment of writing this doc and the one used throughout it.

## Decrypting an OTA .img file
Firmware decryption (and encryption) is handled by `/lib/libfwutil.so` and more specifically its `decrypt_fw` function, here's what it does:
1. It reads the first 160 bytes of the file into five 32 byte chunks, let's call them f0-f4
2. In this specific firmware, f1 was `XS6_4200_12_VFIT` null padded, f2 was random bytes (`89a30d55ae7c10e2561ffd2e8d1cc2b83eca50937647bf64f03a98756262f550`), f4 was the plaintext length (`58568649` when converted to ascii), f0 and f3 were both zeroes
3. `fw_key_alg` creates the AES key, first it computes the MD5 checksum of (f3+f1), then the MD5 checksum of (f4+f1) and concatenates them. It also computes MD5("Speedport W 724V" + f1) but never uses it
4. It reads the first 32 characters of `V0daf0n5_123@hybR1D@ccesshyf123456789` (so `V0daf0n5_123@hybR1D@ccesshyf1234` and `56789` is dropped)
5. It XORs the concatenated MD5 checksums with the 32 character string, that's the AES key
6. The first 16 bytes of `f2` are the IV
7. `decrypt_fd` then decrypts everything after the first 160 bytes till the end of the file using `AES-256-CBC`
8. f4 (parsed as an ASCII string) tells us the plaintext length, it is used to trim the PKCS#7 padding
9. If the resulting file is smaller than 32 bytes it aborts
10. The decrypted file is gzip compressed

<br>The firmware can be decrypted using the `decrypt_fw.py` python script, providing the input and output (eg. `XS6_4200_12_all_decrypted.img`) paths as arguments.
<br>Once that's done `binwalk` can be used to decompress the decrypted image
```sh
binwalk -e XS6_4200_12_all_decrypted.img
```
a directory named `extractions` will be created and the resulting file will be at `./extractions/XS6_4200_12_all_decrypted.img.extracted/A0/decompressed.bin`
```sh
binwalk -Me decompressed.bin
```
The command above should extract all partition in theory. It failed to find the `sasquatch` binary on Arch Linux, however, so I had to use dd
```sh
dd if=decompressed.bin of=voda.sqsh bs=1 skip=384
unsquashfs voda.sqsh
```
`bs=1` is pretty slow so feel free to adjust.
<br>Once you do this you should have the root filesystem.

## Emulating using QEMU
On Arch Linux I had to get `qemu-user-static` and `qemu-user-static-binfmt`, depending on the distro package names may vary. Then I copied `$(which qemu-arm-static)` to the root of the root filesystem. Once you do all that you can start the emulator using
```sh
sudo chroot . /qemu-arm-static -E LD_LIBRARY_PATH=/lib /bin/sh
```
and then run
```sh
etc/rcS
```
to begin the initialization process which will take a few minutes to return to `#`
<br>Once it finishes the web server will be accessible at https://[::1]/ but it will throw you to remote login which is broken. I haven't fixed that yet.
