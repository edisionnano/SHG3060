# SHG3060
Security analysis of the Sercomm SHG3060 router also known as the Greek Vodafone Power Station WiFi 6, the Greek Vox 3.0 and VD5244BV2

## Sections
➣ [Web Analysis](Web) - Deep dive into the SJCL encryption used on protected API endpoints, login flow, exposing hidden settings, dissecting cookies and the `csrf_token` and everything else you need to make automation scripts

➣ [The Private Key](Private_Key) - Analysis of the derivation algorithm and instructions to retrieve your router's private key via a smart brute force attack

➣ [Configuration Files](Configs) - Script to unpack and repack `/etc/default.xml`, the `configurationBackup.cfg` file exported by the router's web interface and other config files

➣ [Firmware Analysis](Firmware) - Decrypting OTA firmware and emulating it with QEMU

➣ [Misc Stuff](Misc) - Other findings that haven't been put to use yet


## Other Routers
Other Sercomm routers provided by Greek ISPs. Briefly covered in case similarities are found.

➣ [Speedport W 724V Type Ci](Other_Routers/W724V) - Probably the first Sercomm router provided by a Greek ISP. This one is from 2013 and was provided by OTE (now Cosmote Telekom)

➣ [Three 4g+ Hub ( Sercomm LTE2122GR )](Other_Routers/LTE2122GR) - 4G+ router by UK ISP Three, software is actully made by Vodafone and is pretty close to the SHG3060. The hardware is closer to the H300S
