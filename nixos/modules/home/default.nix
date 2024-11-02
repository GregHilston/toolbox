{ vars, pkgs, ... }:

{
  imports = [
    ../programs/tui/git
    ../programs/tui/neovim
    ../programs/tui/zsh
    ../programs/gui/alacritty
  ];

  nixpkgs = {
    config = {
      allowUnfree = true;
      allowUnfreePredicate = _: true;
    };
  };

  home = {
    username = "${vars.user}";
    homeDirectory = "/home/${vars.user}";
    packages = with pkgs; [
      bitwarden
      chromium
      discord
      dmenu
      firefox
      ncdu
      obsidian
      ollama
      slack
      spotify
      ripgrep
      slack
      spotify
      vlc
      vscode
      firefox

      # fonts
      jetbrains-mono
    ];
  };

  programs.home-manager.enable = true;

  # https://nixos.wiki/wiki/FAQ/When_do_I_update_stateVersion
  home.stateVersion = "24.05";
}
