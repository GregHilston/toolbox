{
  inputs,
  outputs,
  lib,
  config,
  pkgs,
  vars,
  ...
}: {
  imports = [
    ./hardware-configuration.nix
    ../../../modules/common
    ./steam.nix
  ];

  networking.hostName = "nixos-vm";

  boot.loader.grub = {
    enable = true;
    device = "/dev/sda"; # Typical for VMs
    useOSProber = false; # Usually not needed in VMs
  };

  gaming.enable = true;

  services.spice-vdagentd.enable = true;
  services.qemuGuest.enable = true;

  services.openssh = {
    enable = true;
    ports = [22];
    settings = {
      PasswordAuthentication = true;
      AllowUsers = null; # Allows all users by default. Can be [ "user1" "user2" ]
      UseDns = true;
      X11Forwarding = false;
      PermitRootLogin = "prohibit-password"; # "yes", "without-password", "prohibit-password", "forced-commands-only", "no"
    };
  };
}
