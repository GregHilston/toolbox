{
  description = "ghilston's Nix Config";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-24.05";
    nixpkgs-unstable.url = "github:nixos/nixpkgs/nixos-unstable";
    home-manager = {
      url = "github:nix-community/home-manager/release-24.05";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs = { self, nixpkgs, home-manager, ... }@inputs:
    let
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
          inherit inputs vars;
        };
        modules = [
          ./hosts/isengard
          home-manager.nixosModules.home-manager
          {
            home-manager = {
              useGlobalPkgs = true;
              useUserPackages = true;
              extraSpecialArgs = { inherit vars; };
            };
          }
        ];
      };
    };
}