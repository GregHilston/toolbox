{
  inputs,
  vars,
  pkgs,
  ...
}: {
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
