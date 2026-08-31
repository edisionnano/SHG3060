# Speedport Plus 2
This is a very popular router provided by Cosmote Telekom in Greece, Croatia and other countries. There are two variants of this router, a Sercomm one and an Arcadyan one. The codename of the Sercomm model is VD4224BDT. It's the only black Speedport.

## Firmware Analysis
Both variants have OTA images that are not encrypted. You can get them from the [Gr_ISP_Router_Firmware](https://github.com/k-marios/Gr_ISP_Router_Firmware/tree/main/Cosmote) repo and extract them using `binalk -Me`

## The User Configuration File
The Arcadyan version reads a secret from NVRAM which I couldn't determine without a dump.
<br>The Sercomm version asks the user for a password and then outputs a file called `configurationBackup.cfg` that is internally referred to as `VD4224BDT_Config.cfg` and starts with `Salted__`
<br>We can decrypt it pretty easily using OpenSSL. I used `12345678` as the password for this example
```sh
openssl enc -d -aes256 -pass pass:12345678 \
  -in VD4224BDT_Config.cfg \
  -out VD4224BDT_Config.tgz
```
Once we decrypt it we can decompress it using `tar` like so
```
tar -xzf VD4224BDT_Config.tgz
```
Everything inside is plaintext, the file `psi_wifi` is compressed using `lzw`. The script `decompress_psi_wifi.py` can be utilized to decompress it.