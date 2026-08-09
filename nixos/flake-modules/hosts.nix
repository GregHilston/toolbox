# NixOS + nix-darwin host definitions.
#
# Each host used to repeat an identical specialArgs + module list; the mkNixos/
# mkDarwin helpers below collapse that boilerplate so a host is one entry
# (system + module path + any host-specific extra modules / vars overrides).
{inputs, ...}: let
  inherit (inputs) nixpkgs nixos-wsl nixos-hardware home-manager stylix darwin;

  vars = import ../config/vars.nix {inherit (nixpkgs) lib;};

  # nixpkgs config shared by every NixOS and Darwin host: our overlays and
  # allowUnfree. Previously duplicated across common/darwin system + home modules.
  nixpkgsModule = {
    nixpkgs = {
      overlays = [
        inputs.nur.overlays.default
        inputs.nix-vscode-extensions.overlays.default
      ];
      config.allowUnfree = true;
      # bitwarden-desktop (isengard/mines) currently pins Electron 39, which
      # nixpkgs now marks EOL/insecure. Allow just that version until nixpkgs
      # moves Bitwarden to a supported Electron (then drop this line). Only the
      # x86 GUI hosts pull it; it's a no-op everywhere else.
      config.permittedInsecurePackages = ["electron-39.8.10"];
    };
  };

  # Home-manager wiring shared by every NixOS *and* Darwin host — the option
  # paths are identical in both module systems, so one module serves both.
  # useGlobalPkgs makes home-manager reuse the system nixpkgs (with our shared
  # overlays + allowUnfree) instead of building its own private instance.
  #
  # `vars` comes from specialArgs rather than the closure above, so per-host
  # overrides (citadel's user name) apply here too. The profile itself is
  # attached by the host's own config: modules/common for NixOS workstations,
  # modules/darwin/home.nix for the Macs, and inline for rohan.
  homeManagerModule = {
    inputs,
    vars,
    ...
  }: {
    home-manager = {
      useGlobalPkgs = true;
      useUserPackages = true;
      backupFileExtension = "backup";
      extraSpecialArgs = {inherit inputs vars;};
    };
  };

  mkNixos = {
    system,
    modulePath,
    extraModules ? [],
    hostVars ? vars,
  }:
    nixpkgs.lib.nixosSystem {
      inherit system;
      specialArgs = {
        inherit inputs;
        vars = hostVars;
      };
      modules =
        [
          modulePath
          nixpkgsModule
          stylix.nixosModules.stylix
          home-manager.nixosModules.home-manager
          homeManagerModule
        ]
        ++ extraModules;
    };

  mkDarwin = {
    modulePath,
    system ? "aarch64-darwin",
    extraModules ? [],
    hostVars ? vars,
  }:
    darwin.lib.darwinSystem {
      inherit system;
      specialArgs = {
        inherit inputs;
        vars = hostVars;
      };
      modules =
        [
          modulePath
          nixpkgsModule
          home-manager.darwinModules.home-manager
          homeManagerModule
        ]
        ++ extraModules;
    };
in {
  flake.nixosConfigurations = {
    # Desktop is opt-in (enableGui). foundation (WSL) and home-lab (headless
    # Proxmox server) stay console-only; isengard and mines are GUI machines.
    foundation = mkNixos {
      system = "x86_64-linux";
      modulePath = ../hosts/vms/foundation;
      extraModules = [nixos-wsl.nixosModules.default];
      hostVars = vars // {enableGui = false;};
    };

    isengard = mkNixos {
      system = "x86_64-linux";
      modulePath = ../hosts/pcs/isengard;
      extraModules = [nixos-hardware.nixosModules.lenovo-thinkpad-t420];
      hostVars = vars // {enableGui = true;};
    };

    home-lab = mkNixos {
      system = "x86_64-linux";
      modulePath = ../hosts/vms/home-lab;
      hostVars = vars // {enableGui = false;};
    };

    # Writerdeck — console-only, distraction-free writing machine.
    # See: https://veronicaexplains.net/my-first-writerdeck/
    rohan = mkNixos {
      system = "x86_64-linux";
      modulePath = ../hosts/pcs/rohan;
    };

    mines = mkNixos {
      system = "aarch64-linux";
      modulePath = ../hosts/vms/mines;
      hostVars = vars // {enableGui = true;};
    };
  };

  flake.darwinConfigurations = {
    dungeon = mkDarwin {modulePath = ../hosts/macs/dungeon;};

    moria = mkDarwin {modulePath = ../hosts/macs/moria;};

    # Mozilla work machine: override the user name (drives git identity, home dir).
    citadel = mkDarwin {
      modulePath = ../hosts/macs/citadel;
      hostVars = vars // {user = vars.user // {name = "greghilston";};};
    };
  };
}
