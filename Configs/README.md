# Configuration Files
The router has many different kinds of configuration files, this doc will focus on three of them.

## /etc/default.xml
This is the file that, as the name suggests, contains the default configuration values that are applied when the router is reset to factory settings through the `RESET` button on the back.<br>
The router calls `crypt_decrypt_file2buffer_c` from `/lib/libsex_crypt.so` to decrypt it which works like that:
1. It reads a 64byte signature at offset 0, the first 32 bytes are a SHA256 hash, the rest 32 are padding
2. It calls `crypt_get_default_key` which reads 96 bytes at offset 100 of the .xml file into 24 4byte chunks
3. They are then descrambled using the same function the public key was using; chunks in even positions (0,2,4,etc.) stay as is while those in odd positions (1,3,5,etc.) are placed in the opposite order. The new position is determined by doing chunk count minus current position. So if we have an array with 8 chunks, the second chunk (position 1) goes to position 8-1=7
4. It computes MD5 hashes of the first and last 32 bytes of this 96 byte buffer
5. It concatenates the hashes to form a 256bit key
6. The middle bytes (32-48) are the IV
7. It computes the SHA256 hash of the file using `crypt_digital_signature` from offset 100 till the end of file. If it doesn't match the value from the first step, it exits
8. Bytes from offset 300 till the end of the file are encrypted using `AES-256-CBC`, it decrypts them using the derived default key and IV from the previous steps
9. Reads the last byte to learn how many bytes of PKCS#7 padding there are and strips them

<br>The script `default_xml_tool.py` can be used to decrypt the `default.xml` file.
<br>The script can also re-pack it after editing, this will be useful should we find an exploit that allows as to write to the filesystem.
<br><br>The most interesting finding in the 20 thousand line XML file is the following block:
```xml
<PARAMETER name="Username" type="string" value="admin" writable="1" encryption="0" />
<PARAMETER name="Password" type="string" value="w1$%FL_s3r-0M22!" writable="1" encryption="1" password="1" />
<PARAMETER name="Language" type="string" value="gr" writable="1" encryption="0" />
<PARAMETER name="X_VODAFONE_Group" type="string" value="admin" writable="1" encryption="0" enumeration="user,support,admin" />
<PARAMETER name="X_VODAFONE_Permission" type="string" value="cli" writable="1" encryption="0" />
<PARAMETER name="X_VODAFONE_AccessMode" type="string" value="lan" writable="1" encryption="0" enumeration="lan,wan,all" />
```
The password of the `admin` user is `w1$%FL_s3r-0M22!` but that account doesn't have web interface access.

## /mnt/0 configurations
There are files for all firmware groups in this path (`admin`,`user`,`support`) as well as backup files (`admin.b`,`user.b`,`support.b`). All the changes made are written into these files. When we backup/restore our settings these files are involved. They are decrypted using `crypt_decrypt_file2buffer_p` from `/lib/libsex_crypt.so`.
<br>Here's how that function works:
1. Reads the first 64 bytes, that's the SHA256 hash
2. Computes the SHA256 hash of the file using `crypt_digital_signature` from offset 100 till the end of file. If it doesn't match the value from the first step, it exits
3. If it matches, it gets the private key and IV by calling `crypt_get_private_key`
4. Bytes from offset 300 till the end of the file are encrypted using `AES-256-CBC`, it decrypts them using the derived default key and IV from the previous steps
5. Reads the last byte to learn how many bytes of PKCS#7 padding there are and strips them

<br>Over all pretty similar to `crypt_decrypt_file2buffer_c` but uses the private key instead.
<br>You can run the script `decrypt_mnt0.py` providing the path to the file as the sole argument to decrypt it into a plaintext `configuration.xml` file.
<details>
  <summary>/mnt/0/admin from the emulator</summary>

```xml
<DATAMODEL>
    <OBJECT name="Device." type="object" writable="0" encryption="0" >
        <OBJECT name="DeviceInfo." type="object" writable="0" encryption="0" >
            <PARAMETER name="X_VODAFONE_RebootCause" type="string(256)" value="PowerOff" writable="1" encryption="0" function="GetRebootCause" userSetGroup="admin" />
        </OBJECT>
        <OBJECT name="ManagementServer." type="object" writable="0" encryption="0" >
            <PARAMETER name="X_VODAFONE_CONURLPrefix" type="string(33)" value="7MwsBd2Jw3X59U7f4v2heUSRky000000" writable="1" encryption="0" userSetGroup="admin" />
        </OBJECT>
        <OBJECT name="Services." type="object" writable="0" encryption="0" >
            <OBJECT name="X_VODAFONE_SuperWiFi." type="object" writable="0" encryption="0" >
                <PARAMETER name="UUID" type="string" value="0b19935c-16a9-48bf-98d0-f4b0ec1b281d" writable="1" encryption="0" userSetGroup="admin" />
            </OBJECT>
        </OBJECT>
        <OBJECT name="IP." type="object" writable="0" encryption="0" >
            <OBJECT name="Interface." type="object" writable="1" encryption="0" >
                <OBJECT name="23." type="object" writable="1" encryption="0" >
                    <PARAMETER name="Name" type="string(64)" value="eth5.17" writable="1" encryption="0" userSetGroup="admin" />
                </OBJECT>
                <OBJECT name="22." type="object" writable="1" encryption="0" >
                    <PARAMETER name="Name" type="string(64)" value="eth5.16" writable="1" encryption="0" userSetGroup="admin" />
                </OBJECT>
                <OBJECT name="21." type="object" writable="1" encryption="0" >
                    <PARAMETER name="Name" type="string(64)" value="ppp15" writable="1" encryption="0" userSetGroup="admin" />
                </OBJECT>
                <OBJECT name="20." type="object" writable="1" encryption="0" >
                    <PARAMETER name="Name" type="string(64)" value="ppp14" writable="1" encryption="0" userSetGroup="admin" />
                </OBJECT>
                <OBJECT name="19." type="object" writable="1" encryption="0" >
                    <PARAMETER name="Name" type="string(64)" value="ppp13" writable="1" encryption="0" userSetGroup="admin" />
                </OBJECT>
                <OBJECT name="18." type="object" writable="1" encryption="0" >
                    <PARAMETER name="Name" type="string(64)" value="usb0" writable="1" encryption="0" userSetGroup="admin" />
                </OBJECT>
                <OBJECT name="17." type="object" writable="1" encryption="0" >
                    <PARAMETER name="Name" type="string(64)" value="ppp11" writable="1" encryption="0" userSetGroup="admin" />
                </OBJECT>
                <OBJECT name="16." type="object" writable="1" encryption="0" >
                    <PARAMETER name="Name" type="string(64)" value="ppp10" writable="1" encryption="0" userSetGroup="admin" />
                </OBJECT>
                <OBJECT name="15." type="object" writable="1" encryption="0" >
                    <PARAMETER name="Name" type="string(64)" value="nas10.35.9" writable="1" encryption="0" userSetGroup="admin" />
                </OBJECT>
                <OBJECT name="14." type="object" writable="1" encryption="0" >
                    <PARAMETER name="Name" type="string(64)" value="nas10.36.8" writable="1" encryption="0" userSetGroup="admin" />
                </OBJECT>
                <OBJECT name="13." type="object" writable="1" encryption="0" >
                    <PARAMETER name="Name" type="string(64)" value="ppp7" writable="1" encryption="0" userSetGroup="admin" />
                </OBJECT>
                <OBJECT name="12." type="object" writable="1" encryption="0" >
                    <PARAMETER name="Name" type="string(64)" value="ppp6" writable="1" encryption="0" userSetGroup="admin" />
                </OBJECT>
                <OBJECT name="11." type="object" writable="1" encryption="0" >
                    <PARAMETER name="Name" type="string(64)" value="eth0.5" writable="1" encryption="0" userSetGroup="admin" />
                </OBJECT>
                <OBJECT name="10." type="object" writable="1" encryption="0" >
                    <PARAMETER name="Name" type="string(64)" value="eth0.4" writable="1" encryption="0" userSetGroup="admin" />
                </OBJECT>
                <OBJECT name="9." type="object" writable="1" encryption="0" >
                    <PARAMETER name="Name" type="string(64)" value="eth0.3" writable="1" encryption="0" userSetGroup="admin" />
                </OBJECT>
                <OBJECT name="8." type="object" writable="1" encryption="0" >
                    <PARAMETER name="Name" type="string(64)" value="eth0.2" writable="1" encryption="0" userSetGroup="admin" />
                </OBJECT>
                <OBJECT name="7." type="object" writable="1" encryption="0" >
                    <PARAMETER name="Name" type="string(64)" value="ppp1" writable="1" encryption="0" userSetGroup="admin" />
                </OBJECT>
                <OBJECT name="6." type="object" writable="1" encryption="0" >
                    <PARAMETER name="Name" type="string(64)" value="ppp0" writable="1" encryption="0" userSetGroup="admin" />
                </OBJECT>
            </OBJECT>
            <OBJECT name="Diagnostics." type="object" writable="0" encryption="0" >
                <OBJECT name="TraceRoute." type="object" writable="0" encryption="0" >
                    <PARAMETER name="DiagnosticsState" type="string" value="None" writable="1" encryption="0" enumeration="None,Requested,Complete,Error_CannotResolveHostName,Error_NoRouteToHost,Error_MaxHopCountExceeded,Error_Internal,Error_Other" userSetGroup="admin" />
                </OBJECT>
            </OBJECT>
        </OBJECT>
        <OBJECT name="Users." type="object" writable="0" encryption="0" >
            <OBJECT name="User." type="object" writable="1" encryption="0" >
                <OBJECT name="3." type="object" writable="1" encryption="0" >
                    <PARAMETER name="Password" type="string" value="vodafone" writable="1" encryption="1" password="1" userSetGroup="admin" />
                </OBJECT>
            </OBJECT>
        </OBJECT>
        <OBJECT name="WiFi." type="object" writable="0" encryption="0" >
            <OBJECT name="SSID." type="object" writable="1" encryption="0" >
                <OBJECT name="8." type="object" writable="1" encryption="0" >
                    <PARAMETER name="SSID" type="string(32)" value="Vodafone-Guest" writable="1" encryption="0" userSetGroup="admin" />
                </OBJECT>
                <OBJECT name="5." type="object" writable="1" encryption="0" >
                    <PARAMETER name="SSID" type="string(32)" value="Vodafone-A" writable="1" encryption="0" userSetGroup="admin" />
                </OBJECT>
                <OBJECT name="4." type="object" writable="1" encryption="0" >
                    <PARAMETER name="SSID" type="string(32)" value="Vodafone-Guest" writable="1" encryption="0" userSetGroup="admin" />
                </OBJECT>
                <OBJECT name="1." type="object" writable="1" encryption="0" >
                    <PARAMETER name="SSID" type="string(32)" value="Vodafone-A" writable="1" encryption="0" userSetGroup="admin" />
                </OBJECT>
            </OBJECT>
            <OBJECT name="AccessPoint." type="object" writable="1" encryption="0" >
                <OBJECT name="8." type="object" writable="1" encryption="0" >
                    <OBJECT name="Security." type="object" writable="0" encryption="0" >
                        <PARAMETER name="KeyPassphrase" type="string(63)" value="12345678" writable="1" encryption="0" userSetGroup="admin" />
                        <PARAMETER name="ModeEnabled" type="string" value="WPA2-Personal" writable="1" encryption="0" enumeration="None,WEP-64,WEP-128,WPA-Personal,WPA2-Personal,WPA3-Personal,WPA-WPA2-Personal,WPA2-WPA3-Personal,WPA-WPA2-WPA3-Personal" userSetGroup="admin" />
                    </OBJECT>
                </OBJECT>
                <OBJECT name="5." type="object" writable="1" encryption="0" >
                    <OBJECT name="Security." type="object" writable="0" encryption="0" >
                        <PARAMETER name="KeyPassphrase" type="string(63)" value="12345678" writable="1" encryption="0" userSetGroup="admin" />
                    </OBJECT>
                </OBJECT>
                <OBJECT name="4." type="object" writable="1" encryption="0" >
                    <OBJECT name="Security." type="object" writable="0" encryption="0" >
                        <PARAMETER name="KeyPassphrase" type="string(63)" value="12345678" writable="1" encryption="0" userSetGroup="admin" />
                        <PARAMETER name="ModeEnabled" type="string" value="WPA2-Personal" writable="1" encryption="0" enumeration="None,WEP-64,WEP-128,WPA-Personal,WPA2-Personal,WPA3-Personal,WPA-WPA2-Personal,WPA2-WPA3-Personal,WPA-WPA2-WPA3-Personal" userSetGroup="admin" />
                    </OBJECT>
                </OBJECT>
                <OBJECT name="1." type="object" writable="1" encryption="0" >
                    <OBJECT name="Security." type="object" writable="0" encryption="0" >
                        <PARAMETER name="KeyPassphrase" type="string(63)" value="12345678" writable="1" encryption="0" userSetGroup="admin" />
                    </OBJECT>
                    <OBJECT name="WPS." type="object" writable="0" encryption="0" >
                        <PARAMETER name="PIN" type="string(8)" value="00000000" writable="1" encryption="0" userSetGroup="admin" />
                    </OBJECT>
                </OBJECT>
            </OBJECT>
        </OBJECT>
    </OBJECT>
</DATAMODEL>
```
 
</details>

## configurationBackup.cfg
This is the file that we get from the web interface, encrypted with our own password.
<br>The way this file is created is a bit more complex:
1. `/usr/www-ap/setup.cgi` calls `rcl_backup_cfg` from `/lib/libcfg.so` which is what compiles the file
2. The function reads `/mnt/1/call_log.log` (if it's not empty) and `/tmp/confxml` through a call to `cm_config_export` which is a function of `/lib/libcml_api.so`, a library that communicates through a socket with the `/usr/sbin/cmld` daemon. This daemon is responsible for all things related to configurations.
3. `/usr/sbin/cmld` copies `/mnt/0/{admin,user,support}` (depending on the firmware group), or if it fails `/mnt/0/{admin,user,support}.b`, to `/tmp/confxml`.
4. It calls `sal_misc_get_board_hw_id` from `/lib/libsalx.so` that just reads `Board_HW_ID` from `/tmp/sal/misc.sal` (the value is obtained from NVRAM)
5. Then it creates a file that has a header with that hw id (mine was `4446`, probably the same for every SHG3060), the firmware group (user, support or admin), config size/offset and call log size/offset.
6. After the header is the plaintext call log (it's a csv with the phone calls), then the config and the last 4 bytes are a footer with a CRC32 checksum.
7. The file is then compressed using zlib
8. After that, it calls crypt_xml_key_encryption from /lib/libsex_crypt.so which gets the private key (by calling crypt_get_private_key) and the first 32 characters of the password we used to backup the file. If it's less than 32, the rest becomes zero
9. It computes an md5 hash of those 32 characters and then an md5 hash of the private key and creates an aes256 key by joing the two hashes which it then uses to encrypt the file
10. After the encryption the file is signed using a private key and device certificate, both contained in a PKCS#12 bundle at /usr/local/config.pfx which is protected with the password VD5244BV2
11. Once that's done it's converted to base64 and some stuff are added on the first few lines (`FW Version`, `FW Description`, `FW Create Time`, `FW Group`, `Board S/N`)

<br>`cfg_tool.py` can be used to decrypt and re-encrypt the cfg file. The script will create an .ini file for you to place your private key, IV and .cfg password in. If you plan on repackaging the config you will also need the `config.prx` on the same folder as the script.
