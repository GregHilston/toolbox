{
  description = "ghilston's Nix Config";

  inputs = {
    # Nixpkgs
    # TODO consider setting this to "github:nixos/nixpkgs/nixpkgs-unstable"; instead, IE unstable and no version directly mentioned, IE latest
    nixpkgs.url = "github:nixos/nixpkgs/nixpkgs-unstable";
    nixpkgs-unstable.url = "github:nixos/nixpkgs/nixos-unstable";
    nixos-wsl.url = "github:nix-community/NixOS-WSL/main";
    nixos-hardware.url = "github:NixOS/nixos-hardware/master";
    darwin = {
      url = "github:nix-darwin/nix-darwin/master";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    # Home manager
    home-manager = {
      url = "github:nix-community/home-manager/master"; # eventually replace with github:nix-community/home-manager/release-25.05
      inputs.nixpkgs.follows = "nixpkgs";
    };

    # TODO see if this version is needed...
    stylix.url = "github:danth/stylix/release-24.11";

    nur.url = "github:nix-community/NUR";

    nix-vscode-extensions.url = "github:nix-community/nix-vscode-extensions";
  };

  outputs =
    inputs@{
      self,
      nixpkgs,
      nixpkgs-unstable,
      nixos-wsl,
      nixos-hardware,
      home-manager,
      nix-darwin,
      ...
    }:
    let
      vars = import ./config/vars.nix { inherit (nixpkgs) lib; };

      # Helper function to create the home-manager module configuration
      mkHomeManagerModule =
        { config, ... }:
        {
          home-manager = {
            useUserPackages = true;
            backupFileExtension = "backup";
            users.${vars.user.name} = { };
          };
        };
    in
    {
      nixosConfigurations = {
        foundation = nixpkgs-unstable.lib.nixosSystem {
          system = "x86_64-linux";
          specialArgs = {
            inherit inputs vars;
            outputs = self;
          };
          modules = [
            nixos-wsl.nixosModules.default
            ./hosts/pcs/foundation
            inputs.stylix.nixosModules.stylix
            inputs.home-manager.nixosModules.home-manager
            mkHomeManagerModule
          ];
        };

        isengard = nixpkgs-unstable.lib.nixosSystem {
          system = "x86_64-linux";
          specialArgs = {
            inherit inputs vars;
            outputs = self;
          };
          modules = [
            nixos-hardware.nixosModules.lenovo-thinkpad-t420
            ./hosts/pcs/isengard
            inputs.stylix.nixosModules.stylix
            inputs.home-manager.nixosModules.home-manager
            mkHomeManagerModule
          ];
        };

        vm-x86 = nixpkgs.lib.nixosSystem {
          system = "x86_64-linux";
          specialArgs = {
            inherit inputs vars;
            outputs = self;
          };
          modules = [
            ./hosts/vms/x86_64
            inputs.stylix.nixosModules.stylix
            inputs.home-manager.nixosModules.home-manager
            mkHomeManagerModule
          ];
        };

        vm-arm = nixpkgs.lib.nixosSystem {
          system = "aarch64-linux";
          specialArgs = {
            inherit inputs vars;
            outputs = self;
          };
          modules = [
            ./hosts/vms/arm
            inputs.stylix.nixosModules.stylix
            inputs.home-manager.nixosModules.home-manager
            mkHomeManagerModule
          ];
        };

        mines = nixpkgs.lib.nixosSystem {
          system = "aarch64-linux";
          specialArgs = {
            inherit inputs vars;
            outputs = self;
          };
          modules = [
            ./hosts/vms/mines
            inputs.stylix.nixosModules.stylix
            inputs.home-manager.nixosModules.home-manager
            mkHomeManagerModule
          ];
        };
      };

      darwinConfigurations = {
        moria = inputs.nix-darwin.lib.darwinSystem {
          system = "aarch64-darwin";
          specialArgs = {
            inherit inputs vars;
            outputs = self;
          };
          modules = [
            ({ pkgs, ... }: {
                networking.hostName = "moria";

                # This may no longer needed due to "Determinate is now directly compatible with nix-darwin":
                # https://determinate.systems/posts/nix-darwin-updates/
                #
                # Determinate uses its own daemon to manage the Nix installation that
                # conflicts with nix-darwin’s native Nix management.
                # If we do not disable this, we'll get this error:
                # "error: Determinate detected, aborting activation"
                # To resolve this, turn off nix-darwin’s management of the Nix
                # installation. We do that by:
                #
                nix.enable = false;

                # List packages installed in system profile. To search by name, run:
                # $ nix-env -qaP | grep wget
                environment.systemPackages = [
                  pkgs.vim
                  pkgs.tmux
                  pkgs.htop
                ];

                # Add dock items through nix-darwin's system-level configuration
                system.defaults.dock = {
                  autohide = true;
                  show-recents = false;
                  static-only = true;
                };

                # Add dock entries (apps) through nix-darwin
                system.defaults.dock.persistent-apps = [
                  { app = "/Applications/Safari.app"; }
                  { spacer = { small = false; }; }
                  { spacer = { small = true; }; }
                  { folder = "/System/Applications/Utilities"; }
                ];

                # Necessary for using flakes on this system.
                # Note: Since nix.enable = false, we should not configure nix settings here
                # These settings should be managed by Determinate Systems or configured in /etc/nix/nix.custom.conf
                # nix.settings.experimental-features = "nix-command flakes";

                system.configurationRevision = self.rev or self.dirtyRev or null;

                # Used for backwards compatibility, please read the changelog before changing.
                # $ darwin-rebuild changelog
                system.stateVersion = 6;
                nixpkgs.hostPlatform = "aarch64-darwin";

                # 🍺 Homebrew integration
                homebrew.enable = true;
                homebrew.global.autoUpdate = false;
                homebrew.onActivation.cleanup = "zap";
                homebrew.brews = [ ];
                homebrew.casks = [ "firefox" ];
            })

            # Enable Home Manager integration for macOS
            # inputs.home-manager.darwinModules.home-manager

            # 🏡 Home Manager user config (dock, homebrew, etc.)
            ({
              imports = [
                inputs.home-manager.darwinModules.home-manager
              ];

              users.users.ghilston.home = "/Users/ghilston";
              home-manager.useGlobalPkgs = true;
              home-manager.useUserPackages = true;

              home-manager.users.${vars.user.name} = { pkgs, ... }: {
                home.stateVersion = "24.05"; # Change to your actual version
                home.username = "${vars.user.name}";

                # Disable nix management in home-manager as well
                nix.enable = false;
                programs.nix-index.enable = false;
              };
            })
          ];
        };
      };
    };
}