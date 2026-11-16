# foundation: remote access to the gaming PC

foundation is NixOS-on-WSL2 on Greg's Windows gaming PC (Ryzen 7 5800X, 64 GB, RTX 3080). Agents on moria use it for Windows runs: WSL can launch any Windows exe under `/mnt/c`, on the real GPU.

## What works today (2026-11-14), and what breaks on reboot

- sshd runs only if `services.openssh.enable = true;` is in `hosts/vms/foundation/default.nix`; the common modules leave sshd off on purpose.
- WSL uses NAT, so Windows forwards port 2222 to it: `netsh interface portproxy add v4tov4 listenport=2222 listenaddress=0.0.0.0 connectport=22 connectaddress=<WSL eth0 address>`, plus a firewall rule allowing inbound TCP 2222. Agents connect with `ssh foundation` (Windows' mDNS name) or `ssh foundationts` (its tailnet name); `modules/programs/tui/ssh.nix` adds the port.
- From foundation, use the `ts` names (`moriats`, `dungeonts`, `citadelts`): WSL's DNS bridge drops `.local` lookups and NAT blocks mDNS, so the LAN names fail there (2026-11-16). WSL's mirrored networking mode plus Avahi would fix it.
- The firewall rule and the portproxy entry persist, but WSL's `172.x` address changes each time WSL starts, so the forward breaks. WSL also doesn't start at boot and stops when nothing uses it, and Windows may sleep.

## To make it survive reboots (not yet done)

1. Run Tailscale inside WSL, so foundation joins the tailnet itself and no forward is needed: add `services.tailscale.enable = true;` to foundation's `default.nix`, run `just fr foundation`, then `sudo tailscale up --hostname foundation-wsl` and approve the login. Agents then use `ssh foundation-wsl` on port 22. The Windows Tailscale node keeps the name `foundation`.
2. Start WSL at logon and keep it alive, from PowerShell as Greg: `Register-ScheduledTask -TaskName "WSL keepalive" -Action (New-ScheduledTaskAction -Execute "wsl.exe" -Argument "-d NixOS --exec sleep infinity") -Trigger (New-ScheduledTaskTrigger -AtLogOn)`.
3. Never sleep on AC power: `powercfg /change standby-timeout-ac 0`.
4. The logon task needs Windows to log in at boot: enable automatic sign-in, or expect a Windows Update reboot to stop at the login screen.
5. Once Tailscale in WSL works, remove the portproxy (`netsh interface portproxy delete v4tov4 listenport=2222 listenaddress=0.0.0.0`) and the 2222 firewall rule, update the loser-picks `CLAUDE.md` "Machines" line, and drop `sshPort` from foundation in `config/vars.nix`.

Untested as a whole; the parts are standard WSL and Windows features.
