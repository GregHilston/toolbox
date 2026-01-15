{
  inputs,
  vars,
  pkgs,
  lib,
  ...
}: let
  # Default to GUI enabled if not specified
  enableGui = vars.enableGui or true;
in {
  imports =
    [
      ../programs/tui
    ]
    ++ lib.optionals enableGui [
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

  # Disable KDE Plasma animations for a snappier feel
  # Only set this on GUI-enabled systems to avoid evaluation errors on WSL/headless hosts
  # When enableGui is false, lib.mkIf returns an empty set, which causes NixOS to complain
  # about the kdeglobals.source attribute being accessed but not defined
  xdg.configFile = lib.mkIf enableGui {
    "kdeglobals".text = ''
      [KDE]
      AnimationDurationFactor=0
    '';
  };

  # User packages. IE not system packages
  home = {
    username = "${vars.user.name}";
    homeDirectory = "/home/${vars.user.name}";
    packages = with pkgs;
      [
        # TUI/CLI tools (always installed)
        ncdu
        ollama
        ripgrep
        hugo
        go
        duckdb
        claude-code
      ]
      ++ lib.optionals enableGui [
        # GUI applications (only on non-WSL systems)
        chromium
        dmenu
        obsidian
        vlc
        godot_4
        xclip # X11 clipboard utility
        # texstudio

        # Fonts (needed for GUI)
        nerd-fonts.jetbrains-mono
        jetbrains-mono
        inputs.claude-desktop.packages.${pkgs.stdenv.hostPlatform.system}.claude-desktop
      ]
      ++ (
        if (pkgs.stdenv.hostPlatform.system != "aarch64-linux") && enableGui
        then [
          # x86_64 GUI apps (not on ARM, not on WSL)
          bitwarden-desktop
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
      flake = vars.paths.nixosFlake;
    };
    yazi.enable = true;
  };

  services.mako.enable = false;

  programs.home-manager.enable = true;

  # https://nixos.wiki/wiki/FAQ/When_do_I_update_stateVersion
  home.stateVersion = "24.05";
}
