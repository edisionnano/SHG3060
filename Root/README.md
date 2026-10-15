# Getting Root Access
The following guide explains in detail how to gain root access on the web interface of the router as well as on SSH.
## The steps
1. Format a USB stick to FAT32
2. Download debug firmware `XS6_4200_09d_all.img` from [here](https://github.com/k-marios/Gr_ISP_Router_Firmware/blob/main/Vodafone/Retail/Sercomm/Power_Station_WiFi6/XS6_4200_09d_all.img)
3. Rename it to `VD5244BV2_SERCOMM1.img` and drop it on the root of the USB stick
4. WPS and WiFi buttons are enabled by default, make sure you haven't explicitly disabled them
5. Plug the USB stick on the side USB port of the router
6. Hold the WPS and WiFi buttons down for more than one second
7. The WiFi LED should start flashing
8. It will take a few minutes but the router should successfully install firmware version `XS6_4.2.00.09d`
9. You should now be able to login to ssh as `admin` with the password `w1$%FL_s3r-0M22!`, it will ask for password twice
10. Once in SSH run the following commands
```
config
set cwmp node Device.X_VODAFONE_Management.ShellEnable value 1
set cwmp node Device.Users.User.1.X_VODAFONE_Permission value cli,web
apply
save
quit
```
11. You should now be able to login as `admin` on the web interface too

## Next Steps
### Dumping the Private Key
On a previous section we bruteforced the private key which takes some time, since we have SSH access, it's possible to dump the private key while still on the debug firmware. Once you login to SSH simply use the `sh` command to enter a shell then run `hexdump /mnt/2/.p`, you should get an output that looks like that
```
0000000 fc4d fda4 ebb6 7de1 313c e8dd 1b10 eba9
0000010 eb9f 7ba7 7d97 2797 883e f396 b9a9 25d8
0000020 e437 048f 6753 18c7 6fec a7b4 15da a337
0000030 3135 6466 3437 6338 3136 3261 3561 6536
0000040 6333 6266 3930 3461 3636 6662 3865 3061
0000050 0000 0000 0000 0000 0000 0000 0000 0000
0000060
```
copy that output to a file, for example hexdump.txt and use this command to turn it to a binary
```sh
sed -E 's/^[0-9a-f]+ ?//' hexdump.txt | tr -s ' ' '\n' | grep .   | sed -E 's/(..)(..)/\2\1/' | xxd -r -p > p.bin
```
Then you can use the `decrypt_p.py` script from the previous section to retrieve your key.

### Enable SSH Server
When reverting to production firmware, the SSH server will get disabled. Export a config as admin and decrypt it as mentioned in the previous section, then inject the fields that enable the SSH server
```xml
<OBJECT name="X_VODAFONE_Management." type="object" writable="0" encryption="0" >
<PARAMETER name="ShellEnable" type="boolean" value="1" writable="1" encryption="0" userSetGroup="admin" />
<OBJECT name="Server." type="object" writable="0" encryption="0" >
<OBJECT name="SSHServer." type="object" writable="0" encryption="0" >
<PARAMETER name="Enable" type="boolean" value="1" writable="1" encryption="0" userSetGroup="admin" />
</OBJECT>
</OBJECT>
</OBJECT>
```
repack with cfg tool and restore from the web interface as admin. After that you should get SSH back on production firmware and be able to run the `sh` command to gain full shell access.

### Regarding Telnet
Version 09 is the last with Telnet support, 12 seems to have removed it. You can enable Telnet using `set cwmp node Device.X_VODAFONE_Management.Server.TelnetServer.Enable value 1` but updating to 12 will disable it again.

### Firmware Update
You are currently in debug firmware, you can download the latest production firmware from [here](https://github.com/k-marios/Gr_ISP_Router_Firmware/blob/main/Vodafone/Retail/Sercomm/Power_Station_WiFi6/XS6_4200_12_all.img) and install it from the web interface as admin.
