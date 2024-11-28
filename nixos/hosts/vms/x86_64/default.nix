{ inputs, outputs, lib, config, pkgs, vars, ... }:

{
  imports = [
    ./hardware-configuration.nix
    ../../../modules/common
  ];

  networking.hostName = "nixos-vm";

  boot.loader.grub = {
    enable = true;
    device = "/dev/vda";  # Typical for VMs
    useOSProber = false;  # Usually not needed in VMs
  };

  services.spice-vdagentd.enable = true;
  services.qemuGuest.enable = true;
}
