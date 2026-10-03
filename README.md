# SHG3060
Security analysis of the Sercomm SHG3060 router also known as the Greek Vodafone Power Station WiFi 6, the Greek Vox 3.0 and VD5244BV2

## Sections
➣ [Web Analysis](Web) - Deep dive into the SJCL encryption used on protected API endpoints, login flow, exposing hidden settings, dissecting cookies and the `csrf_token` and everything else you need to make automation scripts

➣ [The Private Key](Private_Key) - Analysis of the derivation algorithm and instructions to retrieve your router's private key via a smart brute force attack

➣ [Configuration Files](Configs) - Script to unpack and repack `/etc/default.xml`, the `configurationBackup.cfg` file exported by the router's web interface and other config files

➣ [Firmware Analysis](Firmware) - Decrypting OTA firmware and emulating it with QEMU

➣ [Misc Stuff](Misc) - Other findings that haven't been put to use yet

➣ [Root Access](Root) - Unlocking the `admin` user on the web interface as well as SSH access

➣ [Practical Lab](Practical_Lab) - Verified follow-up work on an SHG3060 running `XS6_4.2.00.09d`: root shell through the stock CLI, access-point and VoIP observations, a separate LAN lab console, and initial OpenWrt feasibility findings

## Follow-up research on SHG3060 V1

Tests on two privately owned SHG3060 units running `XS6_4.2.00.09d` extend the research above:

- **Stock-firmware root shell:** On one unit, an administrator enabled `Device.X_VODAFONE_Management.ShellEnable` through the SSH CLI. A new session opened `sh` as UID 0, and the setting survived a reboot after `apply` and `save`.
- **LAN access point and voice:** A second unit worked as a LAN-to-LAN access point. Its FXS lines did not register with a local FreePBX server; firmware analysis suggests that the voice daemon is missing the usual WAN interface-binding event. The proposed runtime helper has not been tested.
- **Extending the stock firmware:** A standalone ARM32 program ran on the original kernel, and a separate LAN diagnostic console was tested. Initial flash and device-tree analysis informs future OpenWrt work, but no OpenWrt image has been booted.

The [Practical Lab notes](Practical_Lab) give the procedure, evidence, and limits for each result. They contain no device-specific credentials, configuration backups, or flash images.

## Other Routers
Other Sercomm routers provided by Greek ISPs. Briefly covered in case similarities are found.

➣ [Speedport W 724V Type Ci](Other_Routers/W724V) - Probably the first Sercomm router provided by a Greek ISP. This one is from 2013 and was provided by OTE (now Cosmote Telekom)

➣ [Three 4g+ Hub ( Sercomm LTE2122GR )](Other_Routers/LTE2122GR) - 4G+ router by UK ISP Three, software is actully made by Vodafone and is pretty close to the SHG3060. The hardware is closer to the H300S

➣ [Speedport Plus 2](Other_Routers/VD4224BDT) - Very popular router provided by Cosmote Telekom, also known as VD4224BDT and the black one

➣ [H300S & Plus](Other_Routers/h300s_plus) - The Vodafone H300s and Speedport Plus are two very popular routers in the Greek market with a lot of similarities under the hood
