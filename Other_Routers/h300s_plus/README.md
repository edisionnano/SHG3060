# Vodafone H300s and Speedport Plus
The Vodafone H300s and Speedport Plus are two very popular routers in the Greek market with a lot of similarities under the hood, thus this page covers both. The German Easybox 805 uses the same outer shell as the H300s, however its software is much closer to the SHG3060.

## Decrypting the Firmware
As always, we can find OTA firmware update images on the [Gr_ISP_Router_Firmware](https://github.com/k-marios/Gr_ISP_Router_Firmware) repo.
<br>The images are encrypted. Thanks to [sercomm_fwutils](https://github.com/Psychotropos/sercomm_fwutils), which decrypts the firmware for the Speedport W 724V, I was able to create a script that decrypts them. The firmware encryption is amalgamation of the two types implemented in the script; it uses type 1's header with type 2's key derivation algorithm with null padding instead of key_factor with different offsets for it and the IV.
<br>You can use the `decrypt_fw.py` script to decrypt them and then `binwalk -Me` to extract the rootfs.

## Decrypting the Default XML
Encryption the default.xml files is similar to the firmware encryption, especially to type 2 from `sercomm_fwutils` with another hardcoded salt (`48b526aa1f0552bf3e67f94a9afd3b45`) instead of `key_factor`. The only variable is the firmware version, the router reads `/usr/etc/fw_version` to get it. On the H300s the file reads `1.2.02.08` on the latest firmware, while on the Speedport Plus the latest firmware has `09022001.00.040_OTE4`.
<br>You can use the `decrypt_default_xml.py` script to decrypt these files, as long as the `fw_version` file is on the same directory as the script.
<br>By decrypting `default_GR.xml` we could determine that the `superuser` password is `h27oo$_$UP%_vf22` for the Greek H300s variant, the Turkish passwords were already known.
<br>The Speedport uses a different format parsed by `libcalv2.so`. By reading the default config file we can tell that the priviliged user is `superadmin` with password `p#as3w8rd`. The user, however, seems to be disabled even after a reset.
