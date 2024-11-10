{ inputs, outputs, lib, config, pkgs, vars, ... }:

{
  imports = [
    ./hardware-configuration.nix
    ../../modules/common
  ];

  networking.hostName = "isengard";

  boot.loader.grub = {
    enable = true;
    device = "/dev/sda";
    useOSProber = true;
  };

  powerManagement.powertop.enable = true;
}