# The Darwin workstation home profile.
#
# Layering: ../home/common.nix (identity) ← ../home/workstation.nix (CLI/dev
# baseline, shared with NixOS) ← this file (macOS-only bits). The
# useGlobalPkgs/useUserPackages/backupFileExtension/extraSpecialArgs wiring is
# shared with the NixOS hosts and lives in flake-modules/hosts.nix.
{
  inputs,
  vars,
  pkgs,
  ...
}: let
  open-webui-desktop = pkgs.stdenvNoCC.mkDerivation rec {
    pname = "open-webui-desktop";
    version = "0.0.9";

    src = pkgs.fetchurl {
      url = "https://github.com/open-webui/desktop/releases/download/v${version}/open-webui-arm64.dmg";
      sha256 = "sha256-rTasojUnNkYlfDa9k4pUnRIkvUPzwfQ/96f19NJwF8Q=";
    };

    nativeBuildInputs = [pkgs._7zz];

    sourceRoot = ".";

    unpackPhase = ''
      7zz x $src
    '';

    installPhase = ''
      mkdir -p "$out/Applications"
      app=$(find . -name "*.app" -maxdepth 3 | head -1)
      appName=$(basename "$app")
      cp -r "$app" "$out/Applications/"
      # Nix copies the .app bundle into the content-addressed store path, which
      # breaks the original Apple Developer code signature. macOS's dyld then
      # refuses to load the Electron Framework because the main binary's Team ID
      # no longer matches the framework's Team ID. Ad-hoc re-signing (--sign -)
      # strips all Team IDs and applies a uniform local signature across every
      # nested binary and dylib (--deep), so dyld sees a consistent identity.
      # This is safe for local use; the app just won't pass App Store validation.
      /usr/bin/codesign --deep --force --sign - "$out/Applications/$appName"
    '';

    meta = {
      description = "Open WebUI native desktop app";
      homepage = "https://github.com/open-webui/desktop";
      platforms = ["aarch64-darwin"];
    };
  };
in {
  home-manager.users.${vars.user.name} = {
    imports = [
      ../home/workstation.nix
    ];

    # Darwin-only packages. The shared TUI/CLI baseline is in
    # ../home/workstation.nix. pi-coding-agent comes from homebrew instead, for
    # faster updates.
    home.packages =
      (with pkgs; [
        # Fonts
        nerd-fonts.jetbrains-mono
        jetbrains-mono
      ])
      # GUI apps (installed via nix derivation, linked to ~/Applications/Home Manager Apps/)
      ++ [open-webui-desktop];

    # mflux — Apple Silicon image generation CLI (pip install mflux, not a brew formula).
    # Installed as a global uv tool so `mflux-generate` is on PATH system-wide.
    # This lets the reproduce commands in imagine_loop HTML reports run without
    # needing to be inside the roger project directory.
    home.activation.install-mflux = inputs.home-manager.lib.hm.dag.entryAfter ["installPackages"] ''
      ${pkgs.uv}/bin/uv tool install --upgrade mflux 2>/dev/null || true
    '';

    custom.programs = {
      pi = {
        enable = true;
        defaultModel = "Qwen3.6-35B-A3B-4bit";
      };
      opencode = {
        enable = true;
        defaultModel = "Qwen3.6-35B-A3B-4bit";
        omlxBaseUrl = "http://localhost:8000/v1";
      };
    };
  };
}
