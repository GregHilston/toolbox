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

      # Voice input — hold Caps Lock to dictate. Local speech-to-text (Whisper /
      # Parakeet); audio never leaves the host. The Caps-Lock-to-F18 remap that
      # drives it is ../common/keyd.nix; bind F18 as Handy's push-to-talk key.
      # Builds on aarch64-linux and substitutes from cache, so mines doesn't have
      # to compile webkitgtk (which would risk the OOM documented in CLAUDE.md).
      #
      # xdotool is NOT linked by the nixpkgs build — that build injects text
      # in-process via enigo/XTEST (buildInputs carry libxtst, not libxdo). It's
      # here because upstream's README claims X11 injection needs it, and it's
      # the tool for manually confirming F18 arrives (`xdotool key`, `xev`).
      handy
      xdotool
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

  # Launch Handy with the graphical session (Linux half of "hold Caps Lock to
  # dictate"; the macOS half is a launchd agent in ../darwin/handy.nix). Handy is
  # a tray app and has to already be running for the F18 that keyd emits on a
  # Caps Lock hold to land anywhere — otherwise Caps Lock behaves correctly and
  # nothing dictates. Same enableGui gate as the package itself above.
  #
  # graphical-session.target, not default.target: Handy is webkitgtk + a tray
  # icon, so it needs a display and a running status-notifier host. PartOf ties
  # it to the session so it stops on logout instead of lingering.
  #
  # Untested on Linux, like the keyd half — see ../common/keyd.nix's note.
  systemd.user.services.handy = lib.mkIf enableGui {
    Unit = {
      Description = "Handy — local speech-to-text, push-to-talk on F18";
      After = ["graphical-session.target"];
      PartOf = ["graphical-session.target"];
    };
    Service = {
      ExecStart = "${pkgs.handy}/bin/handy";
      # Plasma can bring the tray up slightly after the target, so give a failed
      # start a few retries rather than leaving dictation dead until next login.
      Restart = "on-failure";
      RestartSec = 5;
    };
    Install.WantedBy = ["graphical-session.target"];
  };

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
