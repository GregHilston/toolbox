{
  inputs,
  vars,
  pkgs,
  lib,
  ...
}: let
  # Desktop is opt-in: hosts enable it via vars.enableGui (set in hosts.nix).
  enableGui = vars.enableGui or false;
  basePackages = import ../../config/base-packages.nix pkgs;
in {
  imports =
    [
      ../programs/tui
    ]
    ++ lib.optionals enableGui [
      ../programs/gui
    ];

  # nixpkgs config (overlays + allowUnfree) comes from the system via
  # home-manager.useGlobalPkgs (set in flake-modules/hosts.nix).

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
    packages =
      # TUI/CLI tools (always installed) — shared with Darwin.
      basePackages.homePackages
      ++ lib.optionals enableGui (with pkgs; [
        # GUI applications (only on non-WSL systems)
        chromium
        dmenu
        obsidian
        vlc
        godot_4
        xclip # X11 clipboard utility
        # texstudio

        # GUI dev tools — nix stand-ins for the macOS Homebrew casks (bruno,
        # dbeaver-community, db-browser-for-sqlite). All build on aarch64-linux.
        bruno
        dbeaver-bin
        sqlitebrowser

        # Fonts (needed for GUI)
        nerd-fonts.jetbrains-mono
        jetbrains-mono
        inputs.claude-desktop.packages.${pkgs.stdenv.hostPlatform.system}.claude-desktop
      ])
      ++ lib.optionals ((pkgs.stdenv.hostPlatform.system != "aarch64-linux") && enableGui) (with pkgs; [
        # x86_64 GUI apps (not on ARM, not on WSL)
        bitwarden-desktop
        discord
        slack
        spotify
      ]);
  };

  # Install searxngr via uv and stow dotfiles after home-manager activation
  home.activation.install-searxngr = lib.hm.dag.entryAfter ["installPackages"] ''
    ${pkgs.uv}/bin/uv tool install --upgrade https://github.com/scross01/searxngr.git 2>/dev/null || true
    # Stow searxngr config from toolbox dotfiles
    if [ -d "$HOME/Git/toolbox/dot/searxngr-config" ]; then
      ${pkgs.stow}/bin/stow -d "$HOME/Git/toolbox/dot" -t "$HOME" searxngr-config 2>/dev/null || true
    fi
  '';

  stylix.targets = {
    firefox.enable = false;
    qt.enable = false;
    # Disable the KDE stylix target on headless hosts: without a Plasma desktop
    # it errors on the undefined kdeglobals source.
    kde.enable = enableGui;
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
