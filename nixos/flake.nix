{
  description = "ghilston's Nix Config";

  inputs = {
    # Nixpkgs
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
    nixos-wsl.url = "github:nix-community/NixOS-WSL/main";
    nixos-hardware.url = "github:NixOS/nixos-hardware/master";
    # Use the full default set (includes Darwin)
    systems.url = "github:nix-systems/default";
    # Home manager
    home-manager = {
      url = "github:nix-community/home-manager";
      inputs.nixpkgs.follows = "nixpkgs";
    };
    stylix.url = "github:danth/stylix";
    stylix.inputs.nixpkgs.follows = "nixpkgs";
    nur.url = "github:nix-community/NUR";
    nix-vscode-extensions.url = "github:nix-community/nix-vscode-extensions";

    # nix-darwin for macOS support
    darwin.url = "github:LnL7/nix-darwin";
    darwin.inputs.nixpkgs.follows = "nixpkgs";
  };

  outputs = inputs @ {
    self,
    nixpkgs,
    systems,
    nixos-wsl,
    nixos-hardware,
    home-manager,
    stylix,
    darwin,
    ...
  }: let
    lib = nixpkgs.lib // home-manager.lib;
    # Support all major systems (Linux and Darwin)
    allSystems = import systems;
    forEachSystem = f: lib.genAttrs allSystems (system: f pkgsFor.${system});
    pkgsFor = lib.genAttrs allSystems (
      system:
        import nixpkgs {
          inherit system;
          config = {allowUnfree = true;};
        }
    );
    vars = import ./config/vars.nix {inherit (nixpkgs) lib;};

    # Helper for home-manager module
    mkHomeManagerModule = {config, ...}: {
      home-manager = {
        useUserPackages = true;
        backupFileExtension = "backup";
        users.${vars.user.name} = {};
      };
    };
  in {
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
          stylix.nixosModules.stylix
          home-manager.nixosModules.home-manager
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
          stylix.nixosModules.stylix
          home-manager.nixosModules.home-manager
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
          stylix.nixosModules.stylix
          home-manager.nixosModules.home-manager
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
          stylix.nixosModules.stylix
          home-manager.nixosModules.home-manager
          mkHomeManagerModule
        ];
      };
    };

    # macOS support (Apple Silicon)
    darwinConfigurations = {
      mines = darwin.lib.darwinSystem {
        system = "aarch64-darwin";
        specialArgs = {
          inherit inputs vars;
          outputs = self;
        };
        modules = [
          ./hosts/darwin/mines # You must create this directory and config
          home-manager.darwinModules.home-manager
          {
            home-manager = {
              useUserPackages = true;
              users.${vars.user.name} = {};
            };
          }
        ];
      };
    };
  };
}
