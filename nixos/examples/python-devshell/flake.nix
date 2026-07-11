{
  description = "Example Python dev environment (direnv + Nix flake)";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = {
    nixpkgs,
    flake-utils,
    ...
  }:
    flake-utils.lib.eachDefaultSystem (system: let
      pkgs = import nixpkgs {inherit system;};
      python = pkgs.python3.withPackages (ps: with ps; [requests]);
    in {
      devShells.default = pkgs.mkShell {
        packages = [python pkgs.ruff];
        shellHook = ''echo "python dev shell · $(python --version)"'';
      };
    });
}
