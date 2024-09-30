{ config, pkgs, user, ... }:

{
  environment.systemPackages = with pkgs; [
    alacritty
    nerdfonts
  ];

  home-manager.users.${user} = {
    programs.alacritty = {
      enable = true;
      font = {
        normalFamily = "Nerd Font";
        size = 12;
      };
    };
  };
}

