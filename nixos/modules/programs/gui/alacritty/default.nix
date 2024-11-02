{ config, pkgs, ... }:

{
  programs.alacritty = {
    enable = true;
    settings = {
      font = {
        normal.family = "Nerd Font";
        size = 12;
      };
    };
  };
}