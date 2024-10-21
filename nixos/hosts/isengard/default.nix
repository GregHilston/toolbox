{ inputs, lib, config, pkgs, vars, ... }:

let
  # Import common configuration
  common = import ../../common.nix { inherit config pkgs; };

  # Get the user value from common.nix
  user = common.user;
in
{
  imports = [
    ./hardware-configuration.nix
    (import ../../modules/programs/gui/alacritty/default.nix { inherit config pkgs user; })  # Pass the user
  ];
}