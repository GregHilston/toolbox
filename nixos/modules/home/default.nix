# The NixOS workstation home profile.
#
# Layering: ./common.nix (identity) ← ./workstation.nix (CLI/dev baseline,
# shared with Darwin) ← this file (Linux-only bits). Keep additions in the
# lowest layer that's still correct — anything that also belongs on the Macs
# goes in ./workstation.nix, not here.
{
  inputs,
  osConfig,
  pkgs,
  lib,
  ...
}: let
  # Desktop is opt-in and has exactly one switch: custom.desktop.enable, set by
  # the host itself (see ../common/desktop.nix). Read it back off the system
  # config so the GUI packages here can never disagree with the desktop stack.
  enableGui = osConfig.custom.desktop.enable;
in {
  imports =
    [
      ./workstation.nix
    ]
    ++ lib.optionals enableGui [
      ../programs/gui
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

  # NixOS-only packages. The shared TUI/CLI baseline is in ./workstation.nix.
  home.packages =
    # Claude Code — NixOS gets it from nixpkgs (declarative). Darwin uses the
    # native self-updating installer in tui/claude.nix instead; that module's
    # installer guard (`! command -v claude`) no-ops here once this is on PATH.
    [pkgs.claude-code]
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

  # Install the searxngr binary via uv. The config itself is stowed on both
  # platforms by ./workstation.nix; on Darwin this install stays manual.
  home.activation.install-searxngr = lib.hm.dag.entryAfter ["installPackages"] ''
    ${pkgs.uv}/bin/uv tool install --upgrade https://github.com/scross01/searxngr.git 2>/dev/null || true
  '';

  stylix.targets = {
    firefox.enable = false;
    qt.enable = false;
    # Disable the KDE stylix target on headless hosts: without a Plasma desktop
    # it errors on the undefined kdeglobals source.
    kde.enable = enableGui;
  };

  services.mako.enable = false;
}
