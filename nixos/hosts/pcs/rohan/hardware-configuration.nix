# Placeholder — auto-generate on the ThinkPad X201 Tablet with:
#   sudo nixos-generate-config --show-hardware-config > hardware-configuration.nix
#
# This stub exists so the flake can evaluate for dry-run testing before
# the writerdeck hardware is provisioned.
{
  lib,
  modulesPath,
  ...
}: {
  imports = [
    (modulesPath + "/installer/scan/not-detected.nix")
  ];

  boot.initrd.availableKernelModules = ["ahci" "ehci_pci" "sd_mod"];
  boot.kernelModules = [];
  boot.extraModulePackages = [];

  fileSystems."/" = {
    device = "/dev/disk/by-label/nixos";
    fsType = "ext4";
  };

  swapDevices = [];

  nixpkgs.hostPlatform = lib.mkDefault "x86_64-linux";
}
