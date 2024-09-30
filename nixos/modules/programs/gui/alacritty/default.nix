{ config, pkgs, ... }:

let
  home-manager = builtins.fetchTarball "https://github.com/nix-community/home-manager/archive/release-24.05.tar.gz";
in
{
  imports =
  [
    (import "${home-manager}/nixos")
  ];

  environment.systemPackages = with pkgs; [
    alacritty
    nerdfonts
  ];

  home-manager.users.ghilston = {
    home.stateVersion = "24.05";

    programs.alacritty = {
      enable = true;
      settings = {
      	font = {
          normal.family = "Nerd Font";
          size = 12;
        };
      };
    };
  };
}

