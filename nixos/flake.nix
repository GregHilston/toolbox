{
  description = "ghilston's Nix Config";

  inputs = {
    # Nixpkgs
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
    nixpkgs-unstable.url = "github:nixos/nixpkgs/nixos-unstable";
    nixos-wsl.url = "github:nix-community/NixOS-WSL/main";
    nixos-hardware.url = "github:NixOS/nixos-hardware/master";
    treefmt-nix.url = "github:numtide/treefmt-nix";

    # Home manager
    home-manager = {
      url = "github:nix-community/home-manager"; # eventually replace with github:nix-community/home-manager/release-25.05
      inputs.nixpkgs.follows = "nixpkgs";
    };

    stylix.url = "github:danth/stylix/release-25.05";
    stylix.inputs.nixpkgs.follows = "nixpkgs";

    nur.url = "github:nix-community/NUR";

    nix-vscode-extensions.url = "github:nix-community/nix-vscode-extensions";
  };

  outputs = inputs @ {
    self,
    nixpkgs,
    nixpkgs-unstable,
    nixos-wsl,
    nixos-hardware,
    home-manager,
    treefmt-nix,
    ...
  }: let
    system = "x86-64-linux";
    vars = import ./config/vars.nix {inherit (nixpkgs) lib;};
    # Define pkgs for treefmt
    pkgs = import inputs.nixpkgs {
      inherit system;
      config.allowUnfree = true;
    };

    # Formatter configuration
    treefmtEval = treefmt-nix.lib.evalModule pkgs ./lib/treefmt.nix;

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
    formatter.${system} = treefmtEval.config.build.wrapper;

    # # Style check for CI, run with `nix flake check`
    checks.${system}.style = treefmtEval.config.build.check self;

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
  };
}
