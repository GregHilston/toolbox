# Formatting + linting, exposed as `nix fmt` and a `nix flake check` check.
#
# treefmt-nix wires these together: alejandra formats, statix flags anti-patterns,
# deadnix removes dead code. `nix fmt` applies fixes; `nix flake check` fails on diff.
{
  perSystem = _: {
    treefmt = {
      projectRootFile = "flake.nix";

      programs = {
        alejandra.enable = true;
        statix.enable = true;
        deadnix = {
          enable = true;
          # Leave unused function args (e.g. `{ pkgs, ... }`) alone — they are
          # part of NixOS/home-manager module signatures, not dead code.
          no-lambda-pattern-names = true;
        };
      };
    };
  };
}
