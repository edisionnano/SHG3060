# Practical Lab: follow-up findings on the SHG3060

This section builds on [edisionnano's SHG3060 research](https://github.com/edisionnano/SHG3060) with observations from two privately owned Sercomm SHG3060 units. The tests below used an SHG3060 V1 running `XS6_4.2.00.09d` unless stated otherwise. The root-shell, Lab Console, and initial OpenWrt checks were recorded on 2 October 2026. They describe what was observed on those units; they are not claims of compatibility with every Vodafone firmware or hardware revision.

No device-specific keys, configuration backups, passwords, SIP credentials, or flash images are included here. Work with your own equipment and keep a separate recovery path before changing persistent settings.

| Topic | Observed result | Remaining limit |
| --- | --- | --- |
| Root shell | Enabled `ShellEnable` in the stock SSH CLI; a fresh SSH session opened `sh` as UID 0. The setting survived one reboot after `apply` and `save`. | Verified on one V1 unit with firmware 09d. |
| Second unit as a LAN access point | LAN-to-LAN networking, main Wi-Fi, and management access worked with the DHCP server and both pools disabled. | The method by which the management IP is assigned needs further checking. |
| FXS ports with FreePBX | SIP configuration persisted, but both lines remained `Initializing` and VoCS was `Down`. | Registration and calls have not been achieved. |
| Lab Console | A separate, manually started LAN service displayed status, hosts, recent events, and diagnostic results. | Its AP apply action is deliberately unavailable while required settings cannot be read reliably. |
| OpenWrt feasibility | A standalone ARM32 program ran on the stock kernel; flash partitions and the active device tree were collected for study. | This does not demonstrate an OpenWrt boot or a restorable full NAND dump. |

## Root shell through the stock CLI

The [root-access guide](../Root/README.md) explains how to obtain administrator SSH access. On the tested 09d unit, that existing SSH session was enough to change the Linux configuration node `Device.X_VODAFONE_Management.ShellEnable`. This requires administrator access to the router first; it is not a way to obtain that access.

From the `view @ SHG3060>` SSH prompt, enter configuration mode and inspect the flag:

```text
config
show cwmp node Device.X_VODAFONE_Management.ShellEnable
```

On the tested unit it was `0`. From the `config @ SHG3060>` prompt:

```text
set cwmp node Device.X_VODAFONE_Management.ShellEnable value 1
show cwmp node Device.X_VODAFONE_Management.ShellEnable
```

The CLI reported `ShellEnable: true`, and a subsequent read returned `ShellEnable: "1"`. In a **new SSH session**, `sh` became available at the `view` prompt. Inside that shell, `/proc/self/status` showed UID and GID `0`. After `apply` and `save` in configuration mode and one reboot, another SSH session still read `"1"` and opened a UID 0 shell.

`ConsoleEnable` remained `0`; the result concerns the SSH session, not a serial console. The U-Boot environment variable with a similar name is separate from this Linux configuration node. No bootloader, NAND partition, or firmware image was modified for this test.

## Access-point and VoIP experiment

A second SHG3060 was configured as a LAN-to-LAN access point. The main Wi-Fi network stayed active, while its DHCP server and two DHCP pools were disabled. A separate primary router supplied the network. The tested unit remained reachable for management.

The two FXS ports were configured as SIP extensions on a local FreePBX server. Their settings persisted, but both lines remained `Initializing` with `VoCS status: Down`. This is an **incomplete experiment**, not a working FreePBX integration.

Runtime and offline firmware analysis indicate a missing interface-binding event. The voice daemon starts in GSM mode when it receives no WAN-up event. The diagnostic `vgw set wanup 1` changed its mode to NET, but did not supply a usable IP address and interface or register the lines. In the extracted 09d firmware, `rcl_start_wan_service` leads to `rcl_voice_update_bind_interface(ip, ifname, wan_id)`, which sends a bind message followed by a refresh to `/var/voice/voip_cli.sock`. A LAN-only access point does not follow the usual voice WAN-up path. This is a supported explanation for the observed state, **not a runtime-proven fix**.

An ARM32 helper was assembled to send the two messages for the bridge interface. It has **not** been executed on the router. Sending the messages successfully would not by itself prove SIP registration or working calls; those would require separate checks of registration, audio, DTMF, and behaviour after reboot.

## Separate LAN Lab Console

A small diagnostic web service was run manually alongside the original firmware interface on the second unit. It exposed status, connected hosts, recent events, ping results, and an access-point preview over HTTPS on a separate LAN port. Login was required, and the service was restricted to the LAN through the router firewall. It was not configured for automatic startup or WAN access.

The preview could read the DHCP server flag through the available local API, but could not safely read both DHCP pool states. Consequently, the AP apply action returned an unsupported response without changing configuration. The interactive vendor CLI separately showed all three DHCP flags disabled. This distinction matters: a correct observed state does not make an automated write path safe or complete.

The lab service's source and credentials are not part of this section. Its existence is an example of adding a diagnostic service to the stock firmware, not an installation guide.

## Initial OpenWrt feasibility work

The tested unit reported a Broadcom BCM63146_B0, two AArch64 CPUs, 512 MiB RAM, 512 MiB NAND, and Linux 4.19.183. Its userspace includes ARM32 programs. A small standalone ARM32 test executable was copied to writable storage, checked by SHA-256, run successfully, and removed. This establishes that an additional ARM32 program can run on the stock kernel; it does **not** establish OpenWrt package compatibility.

Ten individual flash-partition images were copied and their transferred sizes and SHA-256 values checked. A separate 512 MiB full-MTD read produced a different hash on a second read, so it is only a diagnostic snapshot, **not a verified restorable backup**. Standard MTD reads also omit NAND OOB/spare bytes.

The active device-tree blob was extracted from a boot partition. It is useful for mapping hardware, but it is not a complete OpenWrt device definition. The observed U-Boot path verified RSA signatures and component hashes for its FIT image. Booting a replacement kernel or complete OpenWrt image remains untested. No flash write was performed as part of this study.

## Evidence boundary

These findings come from the stated device/firmware tests, CLI output, boot observations, and offline analysis of the matching firmware. The root-shell and ARM32 execution results were observed on hardware. The VoIP binding explanation is based on runtime symptoms plus reverse engineering; the proposed helper and a complete OpenWrt boot remain untested. Future results should be recorded with the exact firmware, hardware revision, observed output, and whether they were reproduced after reboot.
