# Dev shell + git hooks.
#
# Replaces the standalone shell.nix and the hand-rolled scripts/hooks/*:
#   * `nix develop` gives a reproducible env (treefmt + the tools the justfile uses)
#     and installs the git hooks on entry.
#   * pre-commit runs treefmt (alejandra + statix + deadnix) on staged files.
#   * pre-push runs `nix flake check` so broken configs never reach the remote.
{
  perSystem = {
    config,
    pkgs,
    ...
  }: {
    pre-commit.settings.hooks = {
      treefmt = {
        enable = true;
        package = config.treefmt.build.wrapper;
      };

      flake-check = {
        enable = true;
        name = "nix flake check";
        entry = "nix flake check";
        pass_filenames = false;
        stages = ["pre-push"];
      };
    };

    devShells.default = pkgs.mkShell {
      inputsFrom = [config.treefmt.build.devShell];
      shellHook = config.pre-commit.installationScript;
      packages = with pkgs; [
        git
        just
        nh
        nix-output-monitor
        nvd
      ];
    };
  };
}
