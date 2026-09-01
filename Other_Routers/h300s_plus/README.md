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

## Decrypting the Configuration Backup
Both routers encrypt their configs the same way, the only differentiating factor is the `/etc/productclass` file it reads; on the H300s it is empty while on the Speedport Plus it is `W724VCi` which is the previous Speedport model. On the H300s the config is encrypted once more with the password the user provided.
<br>You can use the `cfg_tool.py` script to decode and reencode the config. Speedport Plus does not need a password to be provided.
<br>Once decoded the VOIP passwords become accessible.

## Enabling Telnet on the Plus
We can manipulate the config to enable Telnet on the Speedport Plus. After
```xml
<OBJECT name="Device." type="object" writable="0" >
```
After that, simply append
```xml
<OBJECT name="X_SC_Management." type="object" writable="0" >
<OBJECT name="TelnetServer." type="object" writable="0" hidden="3" >
<PARAMETER name="Enable" type="boolean" value="1" writable="1" />
<PARAMETER name="Port" type="unsignedInt[0:65535]" value="23" writable="1" />
</OBJECT>
</OBJECT>
```
Reencrypt and restore the file and telnet should be enabled.
<br>Looking at the `sc_cli` and `login` binaries, the only account that works on lan is `superadmin` but it doesn't seem to be enabled. `root` and `tech*` accounts seem to only be accessible from the WAN.
<br>The only path going forward is a modded firmware.