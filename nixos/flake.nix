{
  description = "ghilston's Nix Config";

  inputs = {
    # Nixpkgs
    # TODO consider setting this to "github:nixos/nixpkgs/nixpkgs-unstable"; instead, IE unstable and no version directly mentioned, IE latest
    nixpkgs.url = "github:nixos/nixpkgs/nixos-24.11";
    nixpkgs-unstable.url = "github:nixos/nixpkgs/nixos-unstable";
    nixos-wsl.url = "github:nix-community/NixOS-WSL/main";
    nixos-hardware.url = "github:NixOS/nixos-hardware/master";
    nix-darwin.url = "github:nix-darwin/nix-darwin/nix-darwin-24.11";
    nix-darwin.inputs.nixpkgs.follows = "nixpkgs";

    # Home manager
    home-manager = {
      url = "github:nix-community/home-manager/master"; # eventually replace with github:nix-community/home-manager/release-25.05
      inputs.nixpkgs.follows = "nixpkgs";
    };

    stylix.url = "github:danth/stylix/release-24.11";

    nur.url = "github:nix-community/NUR";

    nix-vscode-extensions.url = "github:nix-community/nix-vscode-extensions";
  };

  outputs = inputs@{ self, nixpkgs, nixpkgs-unstable, nixos-wsl, nixos-hardware, home-manager, nix-darwin, ... }:
    let
      vars = import ./config/vars.nix { inherit (nixpkgs) lib; };

      # Helper function to create the home-manager module configuration
      mkHomeManagerModule = { config, ... }: {
        home-manager = {
          useUserPackages = true;
          backupFileExtension = "backup";
          users.${vars.user.name} = {};
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

             # Determinate uses its own daemon to manage the Nix installation that
             # conflicts with nix-darwin’s native Nix management.
             # If we do not disable this, we'll get this error:
             # "error: Determinate detected, aborting activation"
             # To resolve this, turn off nix-darwin’s management of the Nix
             # installation. We do that by:
             nix.enable = false;

             # List packages installed in system profile. To search by name, run:
             # $ nix-env -qaP | grep wget
             environment.systemPackages = [
               pkgs.vim
               pkgs.tmux
               pkgs.htop
             ];

             # Necessary for using flakes on this system.
             nix.settings.experimental-features = "nix-command flakes";

             system.configurationRevision = self.rev or self.dirtyRev or null;

             # Used for backwards compatibility, please read the changelog before changing.
             # $ darwin-rebuild changelog
             system.stateVersion = 6;
             nixpkgs.hostPlatform = "aarch64-darwin";
           })
         ];
       };
     };
   };
}
