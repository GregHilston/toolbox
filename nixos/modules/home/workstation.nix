# The CLI/dev baseline shared by the NixOS and Darwin workstation profiles.
#
# rohan (the writerdeck) deliberately does NOT import this: it cherry-picks a
# few TUI modules and a short package list instead, so it stays clear of the
# heavier tools in basePackages.homePackages (ollama, go, duckdb, ffmpeg…) that
# have no business on a 2010 ThinkPad. That's why the identity layer lives in
# ./common.nix — rohan takes that and stops there.
{
  pkgs,
  vars,
  lib,
  ...
}: let
  basePackages = import ../../config/base-packages.nix pkgs;
in {
  imports = [
    ./common.nix
    ../programs/tui
  ];

  # nixpkgs config (overlays + allowUnfree) comes from the system via
  # home-manager.useGlobalPkgs (set in flake-modules/hosts.nix).
  home.packages = basePackages.homePackages;

  # Searxngr config — single source of truth is dot/searxngr-config, stowed on
  # both platforms so the two never drift. The binary itself is installed via
  # uv: automatically on NixOS (see ./default.nix), manually on Darwin via
  # ~/Git/toolbox/bin/setup-searxngr.sh.
  home.activation.stow-searxngr = lib.hm.dag.entryAfter ["writeBoundary"] ''
    if [ -d "$HOME/Git/toolbox/dot/searxngr-config" ]; then
      ${pkgs.stow}/bin/stow -d "$HOME/Git/toolbox/dot" -t "$HOME" searxngr-config 2>/dev/null || true
    fi
  '';

  custom = {
    nh = {
      enable = true;
      flake = vars.paths.nixosFlake;
    };
    yazi.enable = true;
  };
}
