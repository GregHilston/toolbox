{
  description = "ghilston's Nix Config";

  inputs = {
    # Nixpkgs
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
    nixos-wsl.url = "github:nix-community/NixOS-WSL/main";
    nixos-hardware.url = "github:NixOS/nixos-hardware/master";
    # Use the full default set (includes Darwin)
    systems.url = "github:nix-systems/default";

    # Flake structure + dev tooling
    flake-parts.url = "github:hercules-ci/flake-parts";
    flake-parts.inputs.nixpkgs-lib.follows = "nixpkgs";
    treefmt-nix.url = "github:numtide/treefmt-nix";
    treefmt-nix.inputs.nixpkgs.follows = "nixpkgs";
    git-hooks.url = "github:cachix/git-hooks.nix";
    git-hooks.inputs.nixpkgs.follows = "nixpkgs";

    # Home manager
    home-manager = {
      url = "github:nix-community/home-manager";
      inputs.nixpkgs.follows = "nixpkgs";
    };
    stylix.url = "github:danth/stylix";
    stylix.inputs.nixpkgs.follows = "nixpkgs";
    nur.url = "github:nix-community/NUR";
    nix-vscode-extensions.url = "github:nix-community/nix-vscode-extensions";
    flake-utils.url = "github:numtide/flake-utils";
    # 2. Override the flake-utils default to your version
    flake-utils.inputs.systems.follows = "systems";
    claude-desktop.url = "github:k3d3/claude-desktop-linux-flake";
    # Do NOT follow our nixpkgs — claude-desktop uses nodePackages.asar which was
    # removed from nixpkgs-unstable on 2026-03-03. Let it use its own pinned nixpkgs.
    claude-desktop.inputs.flake-utils.follows = "flake-utils";

    # nix-darwin for macOS support
    darwin.url = "github:LnL7/nix-darwin";
    darwin.inputs.nixpkgs.follows = "nixpkgs";
  };

  outputs = inputs:
    inputs.flake-parts.lib.mkFlake {inherit inputs;} {
      # Systems the per-system outputs (formatter, checks, devShells) are built for.
      systems = import inputs.systems;

      imports = [
        inputs.treefmt-nix.flakeModule
        inputs.git-hooks.flakeModule
        ./flake-modules/hosts.nix
        ./flake-modules/treefmt.nix
        ./flake-modules/dev.nix
      ];
    };
}
