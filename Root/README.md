# Getting Root Access
The following guide explains in detail how to gain root access on the web interface of the router as well as on SSH and Telnet. The process is quite involved, it is possible to create a modded firmware package in the future that will do everything and more automatically but for now I am publishing the first ever way to do this.

## The steps
1. First of all you must set up an FTP server on the computer you will be performing this procedure on. I used VSFTPD. Make sure you can login using a username and a password and that you have read and write permissions.
2. Format a USB stick to FAT32
3. Download firmware `XS6_4200_09d_all.img` from [here](Power_Station_WiFi6/XS6_4200_09d_all.img)
4. Rename it to `VD5244BV2_SERCOMM1.img` and drop it on the root of the USB stick
5. WPS and WiFi buttons are enabled by default, make sure you haven't explicitly disabled them
6. Plug the USB stick on the side USB port of the router
7. Hold the WPS and WiFi buttons down for more than one second
8. The WiFi LED should start flashing
9. It will take a few minutes but the router should successfully install firmware version `XS6_4.2.00.09d`
10. You should now be able to login to ssh as `admin` with the password `w1$%FL_s3r-0M22!`, it will ask for password twice
11. Type `debug` and hit enter to access the debug shell
12. If you alrady know your private key (for example through the configuration bruteforce method) skip to step 15.
13. Run `ftpput -u myftpuser -p mypassword 192.168.2.x /private_key /mnt/2/.p` to pull the private key file on the root of your FTP directory
14. Run the [decrypt_p.py](https://github.com/edisionnano/SHG3060/blob/main/Private_Key/Scripts/decrypt_p.py) script to retrieve your private key and IV
15. Pull the admin configuration to the root of your FTP directory using `ftpput -u myftpuser -p mypassword 192.168.2.x /admin_config /mnt/0/admmin`
16. Decrypt the file using [decrypt_mnt0.py](https://github.com/edisionnano/SHG3060/blob/main/Configs/Scripts/decrypt_mnt0.py), just make sure to edit it to fill in your private key and IV
17. Edit the file to explicitly enable SSH and change the admin user's password and permissions. Non `d` firmwares disable SSH and newer firmwares may alter the `admin` password which is why we must set the values explicitly instead of relying on the default configuration.
18. The top of the decrypted file should look like this, green lines are the new code we added (without inclding the plus signs at the start of each line of course)
```diff
 <DATAMODEL>
 <OBJECT name="Device." type="object" writable="0" encryption="0" >
 <OBJECT name="DeviceInfo." type="object" writable="0" encryption="0" >
 <PARAMETER name="X_VODAFONE_RebootCause" type="string(256)" value="PowerOff" writable="1" encryption="0" function="GetRebootCause" userSetGroup="admin" />
 </OBJECT>
+<OBJECT name="X_VODAFONE_Management." type="object" writable="0" encryption="0" >
+<OBJECT name="Server." type="object" writable="0" encryption="0" >
+<OBJECT name="SSHServer." type="object" writable="0" encryption="0" >
+<PARAMETER name="Enable" type="boolean" value="1" writable="1" encryption="0" userSetGroup="admin" />
+</OBJECT>
+</OBJECT>
+</OBJECT>
 <OBJECT name="ManagementServer." type="object" writable="0" encryption="0" >
 <PARAMETER name="X_VODAFONE_CONURLPrefix" type="string(33)" value="" writable="1" encryption="0" userSetGroup="admin" />
 </OBJECT>
 <OBJECT name="Services." type="object" writable="0" encryption="0" >
 <OBJECT name="X_VODAFONE_SuperWiFi." type="object" writable="0" encryption="0" >
 <PARAMETER name="UUID" type="string" value="" writable="1" encryption="0" userSetGroup="admin" />
 </OBJECT>
 </OBJECT>
 <OBJECT name="IP." type="object" writable="0" encryption="0" >
 ```
19. The on `Users.User`
```diff
 <OBJECT name="Users." type="object" writable="0" encryption="0" >
 <OBJECT name="User." type="object" writable="1" encryption="0" >
+<OBJECT name="1." type="object" writable="1" encryption="0" >
+<PARAMETER name="Password" type="string" value="admin" writable="1" encryption="1" password="1" userSetGroup="admin" />
+<PARAMETER name="Language" type="string" value="en" writable="1" encryption="0" userSetGroup="admin" />
+<PARAMETER name="X_VODAFONE_Permission" type="string" value="cli,web" writable="1" encryption="0" userSetGroup="admin" />
+<PARAMETER name="X_VODAFONE_AccessMode" type="string" value="lan,wan" writable="1" encryption="0" enumeration="lan,wan,all" userSetGroup="admin" />
+</OBJECT>
 <OBJECT name="3." type="object" writable="1" encryption="0" >
 <PARAMETER name="Password" type="string" value="8UySy4p7G7Pf" writable="1" encryption="1" password="1" userSetGroup="admin" />
 </OBJECT>
 </OBJECT>
 </OBJECT>
```
20. Save your changes and use the `encrypt_mnt0.py` script to re-encrypt the configuration to a different file, for example `admin_new` and put it on the FTP share's root folder
21. Pull it from the router using `ftpget -u myftpuser -p mypassword 192.168.2.x /mnt/0/admin /admin_new`
22. Reboot the router
23. Once the router boots you should be able to login on the web interface using the new `admin`/`admin` credentials
24. Download the latest production firmware from [here](https://github.com/k-marios/Gr_ISP_Router_Firmware/tree/main/Vodafone/Retail/Sercomm/Power_Station_WiFi6), at the time of writing this the latest is `XS6_4200_12_all.img`
25. As `admin` you can install the firmware update from the web interface
26. Once the router boots to the latest production version you should still be able to login as `admin`/`admin` on SSH and the web interface

## Shell Access
SSH drops you to `sc_cli` which is a very constricted shell, instead of busybox's ash. To exit you have to use the `sh` command but that only works if
```xml
<PARAMETER name="ShellEnable" type="boolean" value="0" writable="1" encryption="0" />
```
is enabled. Sadly we cannot enable through config manipulation so a modded firmware is the only option here.
<br>There are some other interesting options like
```xml
<PARAMETER name="OpenModemEnable" type="boolean" value="0" writable="1" encryption="0" />
```
which debrands other vodafone routers and unlocks more WAN port options and
```xml
<PARAMETER name="ConsoleEnable" type="boolean" value="0" writable="1" encryption="0" />
```
which probably enables UART shell access
