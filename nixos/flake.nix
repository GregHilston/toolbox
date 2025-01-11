{
  description = "ghilston's Nix Config";

  inputs = {
    # Nixpkgs
    nixpkgs.url = "github:nixos/nixpkgs/nixos-24.11";
    nixpkgs-unstable.url = "github:nixos/nixpkgs/nixos-unstable";
    nixos-wsl.url = "github:nix-community/NixOS-WSL/main";
    nixos-hardware.url = "github:NixOS/nixos-hardware/master";

    # Home manager
    home-manager = {
      url = "github:nix-community/home-manager/release-24.11";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    stylix.url = "github:danth/stylix/release-24.11";

    nur.url = "github:nix-community/NUR";

    nix-vscode-extensions.url = "github:nix-community/nix-vscode-extensions";

    flake-utils.url = "github:numtide/flake-utils";

    claude-desktop = {
      url = "github:nonsleepr/claude-desktop-linux-flake";
      inputs = {
        nixpkgs.follows = "nixpkgs";
        flake-utils.follows = "flake-utils";
      };
    };
  };

  outputs = inputs@{ self, nixpkgs, nixpkgs-unstable, nixos-wsl, nixos-hardware, home-manager, ... }:
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

        isengard = nixpkgs.lib.nixosSystem {
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
    };
}
