{
  inputs,
  vars,
  pkgs,
  lib,
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
        packages = with pkgs; [
          # TUI/CLI tools
          ncdu
          ollama
          uv
          ripgrep
          hugo
          go
          duckdb
          claude-code
          yt-dlp
          (python3.withPackages (ps:
            with ps; [
              youtube-transcript-api
            ]))

          # Fonts
          nerd-fonts.jetbrains-mono
          jetbrains-mono

          # GUI apps (installed via nix derivation, linked to ~/Applications/Home Manager Apps/)
          open-webui-desktop
        ];
      };

      custom = {
        nh = {
          enable = true;
          flake = vars.paths.nixosFlake;
        };
        yazi.enable = true;
      };

      programs.home-manager.enable = true;

      home.stateVersion = "24.05";
    };
  };
}
