{
  inputs,
  vars,
  pkgs,
  lib,
  ...
}: let
  basePackages = import ../../config/base-packages.nix pkgs;
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
  home-manager = {
    useUserPackages = true;
    backupFileExtension = "backup";
    extraSpecialArgs = {
      inherit inputs vars;
    };
    users.${vars.user.name} = {
      imports = [
        ../../modules/programs/tui
      ];

      nixpkgs = {
        config = {
          allowUnfree = true;
          allowUnfreePredicate = _: true;
        };
        overlays = [
          inputs.nur.overlays.default
          inputs.nix-vscode-extensions.overlays.default
        ];
      };

      home = {
        username = vars.user.name;
        homeDirectory = "/Users/${vars.user.name}";
        # TUI/CLI baseline shared with NixOS (config/base-packages.nix), plus
        # Darwin-only extras. pi-coding-agent is managed via homebrew for faster updates.
        packages =
          basePackages.homePackages
          ++ (with pkgs; [
            ffmpeg
            # Fonts
            nerd-fonts.jetbrains-mono
            jetbrains-mono
          ])
          # GUI apps (installed via nix derivation, linked to ~/Applications/Home Manager Apps/)
          ++ [open-webui-desktop];
      };

      # mflux — Apple Silicon image generation CLI (pip install mflux, not a brew formula).
      # Installed as a global uv tool so `mflux-generate` is on PATH system-wide.
      # This lets the reproduce commands in imagine_loop HTML reports run without
      # needing to be inside the roger project directory.
      home.activation.install-mflux = inputs.home-manager.lib.hm.dag.entryAfter ["installPackages"] ''
        ${pkgs.uv}/bin/uv tool install --upgrade mflux 2>/dev/null || true
      '';

      # Searxngr config — points to dungeon's SearXNG instance.
      # The binary is installed via uv (run ~/Git/toolbox/bin/setup-searxngr.sh on first use).
      # On NixOS hosts, home.activation handles both install + stow; on Darwin we just
      # declare the config file here and let the user run the setup script for the binary.
      xdg.configFile."searxngr/config.ini".text = ''
        [searxngr]
        searxng_url = https://searxng.grehg2.xyz
      '';

      custom = {
        nh = {
          enable = true;
          flake = vars.paths.nixosFlake;
        };
        yazi.enable = true;
        programs.pi = {
          enable = true;
          defaultModel = "Qwen3.6-35B-A3B-8bit";
        };
        programs.opencode = {
          enable = true;
          defaultModel = "Qwen3.6-35B-A3B-8bit";
          omlxBaseUrl = "http://localhost:8000/v1";
        };
      };

      programs.home-manager.enable = true;

      home.stateVersion = "24.05";
    };
  };
}
