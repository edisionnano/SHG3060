# Speedport W 724V Type Ci
Probably the first Sercomm router provided by a Greek ISP. This one is from 2013 and was provided by OTE (now Cosmote Telekom).

## Firmware Analysis
Firmware can be found [here](https://github.com/k-marios/Gr_ISP_Router_Firmware/tree/main/Cosmote/Sercomm/Speedport_W_724V_Type_Ci). It can be decrypted using [this](https://github.com/Psychotropos/sercomm_fwutils) or [this](https://github.com/jte/sercomm_fwutils_new) and then the regular `binwalk` commands.

## /etc/default.xml
Just like other routers this one has a default configuration file that is used to restore the device to factory defaults. In fact this one has another one too, `/etc/default_098.xml`.
<br>The password that was used to encrypt these files is `jErRy`.
<br>You can use the script `decrypt_default.py` to decrypt them.

## Passwords
`/etc/passwd_file` defines user root with password `root`, the salt is `$1$pWjeboqR$` while `/etc/shadow_file` has the same `root` password but with `qGmxLn8v` as the salt.
<br>There's also a file called `/etc/ClientPassword` containing `zhkankfLYoO969zB`
