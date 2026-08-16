Host configurations, grouped by machine type: `macs/`, `pcs/`, `vms/`. Each
`<type>/<host>/` holds that machine's `default.nix`, and — for hosts running on real
hardware — a generated `hardware-configuration.nix`. The three Macs and the WSL host
(foundation) have no hardware config; nix-darwin and NixOS-WSL supply that themselves.

Hosts are registered in `flake-modules/hosts.nix`, not here. Run `just list-hosts` for the
current list.

The configs are deliberately thin: nearly everything lives in `modules/`, so a host file
should read as a short list of imports plus the handful of facts that are genuinely unique
to that machine.
