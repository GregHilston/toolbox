{ inputs, outputs, lib, config, pkgs, vars, ... }:

{
  imports = [
    ./hardware-configuration.nix
    ../../modules/common
  ];

  networking.hostName = "nixos-vm";

  # VM-specific boot configuration would go here
  boot.loader.grub = {
    enable = true;
    device = "/dev/vda";  # Typical for VMs
    useOSProber = false;  # Usually not needed in VMs
  };

  # VM-specific settings
  services.spice-vdagentd.enable = true;  # If using SPICE
  services.qemuGuest.enable = true;       # If running in QEMU
}