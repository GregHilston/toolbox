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
    username = "${vars.user.name}";
    homeDirectory = "/home/${vars.user.name}";
    packages = with pkgs; [
      chromium
      dmenu
      firefox
      ncdu
      obsidian
      ollama
      ripgrep
      vlc
      vscode
      hugo
      texstudio

      # fonts
      nerdfonts
      jetbrains-mono
    ] ++ (if pkgs.stdenv.hostPlatform.system != "aarch64-linux" then [
      # ARM does not support every package, so only install these if we're not on an ARM basd architecture
      bitwarden
      discord
      slack
      spotify
    ] else []);
  };

  programs.home-manager.enable = true;

  # https://nixos.wiki/wiki/FAQ/When_do_I_update_stateVersion
  home.stateVersion = "24.05";
}
