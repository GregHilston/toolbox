# nixos/hosts/vms/mines/default.nix
{
  inputs,
  outputs,
  lib,
  config,
  pkgs,
  vars,
  ...
}: {
  # Import the generic ARM VM configuration as a base.
  # This pulls in all settings from nixos/hosts/vms/arm/default.nix,
  # including its 'hardware-configuration.nix' and other common VM services.
  imports = [
    ../arm # This refers to nixos/hosts/vms/arm/default.nix
  ];

  # Override the hostname from "nixos-vm" (set in ./arm) to "mines".
  networking.hostName = "mines";

  # Add any other specific configurations for 'mines' here if it needs
  # anything truly unique or different compared to the generic ARM VM.
  # For example:
  # services.something-unique-to-mines.enable = true;
  # environment.systemPackages = with pkgs; [ specific-tool ];
}
