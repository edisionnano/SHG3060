# Three 4g+ Hub ( Sercomm LTE2122GR )
4G+ router by UK ISP Three, software is actully made by Vodafone and is pretty close to the SHG3060. The hardware is closer to the H300S

## Firmware Analysis
A romdump exists for this model, dumped by a user called Dazmatic. The original upload is long gone but I have preserved a copy of it [here](https://drive.google.com/file/d/1_p57vZBBfkdHORvAm6btIjmZTFSQe5S5/view).
<br>There is also a repository dedicated to the analysis and emulation of this specific device and can be found [here](https://github.com/shantur/Three-4G-Hub-Firmware-Analysis).

## Decrypting the User Configuration
The file downloaded is called `Config3UKBox.cfg`. The way the file is encrypted is identical to the SHG3060.
<br>The group config files at `/mnt/0` which are copied to the cfg are not encrypted, for this reason I have created a different `cfg_tool.py` for this router.
<br>Instead of a private key, the public key is used to encrypt the cfg, the same public key as the SHG3060. I have converted it to bytes for simplicity's shake.
<br>The passphrase for `config.pfx` is the model here too, `LTE2122GR`.
<br>I have also hardcoded the password to `abcdefgh`.