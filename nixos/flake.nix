{
  description = "ghilston's Nix Config";

  inputs = {
    # Nixpkgs
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
    nixos-wsl.url = "github:nix-community/NixOS-WSL/main";
    nixos-hardware.url = "github:NixOS/nixos-hardware/master";
    systems.url = "github:nix-systems/default-linux";
    # Home manager
    home-manager = {
      url = "github:nix-community/home-manager"; # eventually replace with github:nix-community/home-manager/release-25.05
      inputs.nixpkgs.follows = "nixpkgs";
    };

    stylix.url = "github:danth/stylix";
    stylix.inputs.nixpkgs.follows = "nixpkgs";

    nur.url = "github:nix-community/NUR";

    nix-vscode-extensions.url = "github:nix-community/nix-vscode-extensions";
  };

  outputs = inputs @ {
    self,
    nixpkgs,
    systems,
    nixos-wsl,
    nixos-hardware,
    home-manager,
    ...
  }: let
    lib = nixpkgs.lib // home-manager.lib;
    forEachSystem = f: lib.genAttrs (import systems) (system: f pkgsFor.${system});
    pkgsFor = lib.genAttrs (import systems) (
      system:
        import nixpkgs {
          inherit system;
          config = {
            allowUnfree = true;
          };
        }
    );
    vars = import ./config/vars.nix {inherit (nixpkgs) lib;};

    # Helper function to create the home-manager module configuration
    mkHomeManagerModule = {config, ...}: {
      home-manager = {
        useUserPackages = true;
        backupFileExtension = "backup";
        users.${vars.user.name} = {};
      };
    };
  in {
    # Format whole configuration with `nix fmt`
    formatter = forEachSystem (pkgs: pkgs.alejandra);

    nixosConfigurations = {
      foundation = nixpkgs.lib.nixosSystem {
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
