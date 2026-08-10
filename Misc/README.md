# Miscellaneous Findings
Interesting and useful findings that didn't fit in any of the other categories and haven't been used to exploit the router yet.

## A potential attack vector
When the WiFi physical buttons at the top of the router (`WIFI` and `WPS`) are enabled (Wi-Fi > General > Enable Wi-Fi and WPS button on your Vodafone Power Station ) the daemon at `/usr/sbin/wifi_pb` runs and listens for them. If both are pressed and held for more than one second it will run /etc/usbScan.sh. The script is this one:
```sh
#!/bin/sh
path=`/usr/bin/find -H /mnt/3/1/mnt/shares/ -maxdepth 3 -name VD5244BV2_SERCOMM*.img|sed -n "1p" 2> /dev/null`
if [ "$path" = "" ]; then
  echo "no FW found!"
  exit 1
else
  strA="-"
  result=$(echo $path | grep "${strA}")
  if [[ "$result" != "" ]]; then
    echo "FW name is illegal"
  else
    strB=" "
    result=$(echo $path | grep "${strB}")
    if [[ "$result" != "" ]]; then
      echo "FW name is illegal"
    else
      if [ -L $path ]; then
        echo "FW is a symbolic link file"
        exit 1
      fi
      echo "Upgrade: FW image is" $path
      num=$RANDOM
      /bin/cp $path ${path}${num}_tmp
      if [ -L "${path}${num}_tmp" ]; then
        echo "Tmp FW is a symbolic link file"
        exit 1
      fi
      /usr/sbin/dualImage_ctrl -dcusr ${path}${num}_tmp -m USB
      echo "FW Upgrade check done!"
    fi
  fi
fi
```
The web interface states that only FAT16, FAT32 and NTFS filesystems are supported but I have confirmed EXT2, EXT3 and EXT4 work just fine.
<br>`/mnt/3/1/mnt/shares/` is where a USB stick gets mounted, where `/mnt/3/1` is a tmpfs mirroring `/`
<br>So what this script does is pretty simple:
1. It checks at the root of the USB stick we plugged if there's a file matching `VD5244BV2_SERCOMM*.img` (for example could be `VD5244BV2_SERCOMM_EVIL.img`)
2. If there is, it gets a random from the shell (`$RANDOM`), an integer in the range 0 - 32767
3. It copies the file to `${path}${num}_tmp` (for example if `$RANDOM` was 1000 it copies it to VD5244BV2_SERCOMM_EVIL.img1000_tmp) using `cp`
4. It performs a check to see if it's a symbolic link but only after running `cp`, if it passes it will call `/usr/sbin/dualImage_ctrl` to perform the update

The issue here is that the shell's `$RANDOM` has a very small range, `cp` WILL follow symlinks before any check runs, the USB stick can use a filesystem that supports symlinks and the script will run as root.
<br>So, theoritcally, we can create 32768 symlinks and overwrite a file with the contents of our fake firmware upgrade file, for example
```sh
for i in $(seq 0 32767); do
     ln -s /etc/default.xml "VD5244BV2_SERCOMM_EVIL.img${i}_tmp";
done
```
I have not tried this yet.

## /etc/passwd and /etc/shadow
`/lib/libhcal.so` creates `/var/cli_pw`, `/var/cli_pw_remote`, `/var/passwd` and `/var/passwd_remote`. `/etc/shadow` and `/etc/passwd` are symlinks to their `/var` counterparts.
<br>A user called nobody is created for specific purposes (like the FTP without login)
```C
SYSTEM("/bin/echo nobody:x:99:99:Nobody:/:/bin/false >> /etc/passwd");
SYSTEM("/bin/echo nobody:x:19000:0:99999:7:-1:99999: >> /etc/shadow");
```
<br>It also creates users `vodafone`, `admin` and `support`.
<br>For the user `vodafone` the password is read from the nvram (`/mnt/2/enduser_pwd`). If that doesn't exist then the password is `vodafone`.
<br>The passwords for `support` and `admin` are read from `/etc/default.xml`
<br>The salt is `$1$SERCOMM$` just like on the javascript code
<br>We can easily replicate the hash algorithm using `perl`
```sh
perl -e 'print crypt("vodafone", "\$1\$SERCOMM\$"), "\n"'
```
