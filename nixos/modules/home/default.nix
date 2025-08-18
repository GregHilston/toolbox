{
  inputs,
  vars,
  pkgs,
  lib,
  ...
}: let
  configPath = "/home/ghilston/vscode-config";
in {
  imports = [
    ../programs/tui
    ../programs/gui
  ];

  nixpkgs = {
    config = {
      allowUnfree = true;
      allowUnfreePredicate = _: true;
    };
  };

  nixpkgs.overlays = [
    inputs.nur.overlays.default
    inputs.nix-vscode-extensions.overlays.default
  ];

  # Symlink settings, keybindings, and extensions
  home.file.".config/Code/User/settings.json".source =
    lib.mkForce (lib.file.mkOutOfStoreSymlink "${configPath}/settings.json");
  # Keybindings
  home.file.".config/Code/User/keybindings.json".source =
    lib.mkForce (lib.file.mkOutOfStoreSymlink "${configPath}/keybindings.json");

  # Optionally, manage extensions with a JSON file
  home.file.".config/Code/User/extensions.json".source =
    lib.mkForce (lib.file.mkOutOfStoreSymlink "${configPath}/extensions.json");

  # User packages. IE not system packages
  home = {
    username = "${vars.user.name}";
    homeDirectory = "/home/${vars.user.name}";
    packages = with pkgs;
      [
        chromium
        dmenu
        ncdu
        obsidian
        ollama
        ripgrep
        vlc
        vscode
        hugo
        texstudio
        godot_4
        go
        duckdb

        # fonts
        nerd-fonts.jetbrains-mono
        jetbrains-mono
        inputs.claude-desktop.packages.${system}.claude-desktop

        # inputs.claude-desktop.packages.${system}.claude-desktop
      ]
      ++ (
        if pkgs.stdenv.hostPlatform.system != "aarch64-linux"
        then [
          # ARM does not support every package, so only install these if we're not on an ARM basd architecture
          bitwarden
          discord
          slack
          spotify
        ]
        else []
      );
  };

  stylix.targets = {
    firefox.enable = false;
    qt.enable = false;
  };

  # Enable/Disable the nh module
  custom = {
    nh = {
      enable = true;
      flake = "${builtins.getEnv "HOME"}/toolbox/nixos";
    };
    yazi.enable = true;
  };

  services.mako.enable = false;

  programs.home-manager.enable = true;

  # https://nixos.wiki/wiki/FAQ/When_do_I_update_stateVersion
  home.stateVersion = "24.05";
}
