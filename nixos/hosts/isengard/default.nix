{ inputs, lib, config, pkgs, vars, ... }:

{
  imports = [
    ./hardware-configuration.nix
    ../../common.nix
  ];

  # You can add isengard-specific configurations here
}