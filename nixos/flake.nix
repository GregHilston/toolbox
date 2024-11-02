{
  description = "ghilston's Nix Config";

  inputs = {
    # Nixpkgs
    nixpkgs.url = "github:nixos/nixpkgs/nixos-24.05";
    nixpkgs-unstable.url = "github:nixos/nixpkgs/nixos-unstable";

    # Home manager
    home-manager = {
      url = "github:nix-community/home-manager/release-24.05";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    stylix.url = "github:danth/stylix/release-24.05";
  };

  outputs = inputs@{ self, nixpkgs, ... }:
    let
      inherit (self) outputs;
      vars = {
        user = "ghilston";
        name = "Greg Hilston";
        email = "Gregory.Hilston@gmail.com";
        location = "$HOME/.nix";
        # terminal = "kitty";
        editor = "nvim";
        shell = "zsh";
      };
    in
    {
      nixosConfigurations.isengard = nixpkgs.lib.nixosSystem {
        system = "x86_64-linux";
        specialArgs = {
          inherit inputs outputs vars;
        };
        modules = [
          ./hosts/isengard
          inputs.stylix.nixosModules.stylix
          {
            home-manager = {
              useGlobalPkgs = true;
              useUserPackages = true;
	            backupFileExtension = "backup2";
            };
          }
        ];
      };
    };
}
