{ config, pkgs, ... }:

{
  imports = [
    ../common.nix
    ../../modules/gaming
  ];
}

