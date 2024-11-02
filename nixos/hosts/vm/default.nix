{ config, pkgs, ... }:

{
  imports = [
    ./hardware-configuration.nix
    ../../modules/gaming
  ];
}

