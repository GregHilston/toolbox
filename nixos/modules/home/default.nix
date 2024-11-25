{ inputs, vars, pkgs, ... }:

{
  imports = [
    ../programs/tui/git
    ../programs/tui/neovim
    ../programs/tui/zsh
    ../programs/gui/alacritty
    ../programs/gui/firefox
    ../programs/gui/vscode
  ];

  nixpkgs = {
    config = {
      allowUnfree = true;
      allowUnfreePredicate = _: true;
    };
  };

  nixpkgs.overlays = [
    inputs.nur.overlay
    inputs.nix-vscode-extensions.overlays.default
  ];

  # User packages. IE not system packages
  home = {
    username = "${vars.user}";
    homeDirectory = "/home/${vars.user}";
    packages = with pkgs; [
      # bitwarden
      chromium
      # discord
      dmenu
      firefox
      ncdu
      obsidian
      ollama
      # slack
      # spotify
      ripgrep
      vlc
      vscode

      # fonts
      nerdfonts
      jetbrains-mono
    ];
  };

  programs.home-manager.enable = true;

  # https://nixos.wiki/wiki/FAQ/When_do_I_update_stateVersion
  home.stateVersion = "24.05";
}
