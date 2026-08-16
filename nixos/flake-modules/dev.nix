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

    # Just enough to run `just validate`, and nothing else.
    #
    # The weekly lock-bump workflow validates a *proposed* flake.lock, and every
    # package it enters a shell for is built from that unproven lock. `default`
    # carries nh (Rust), nix-output-monitor (Haskell), nvd and treefmt's
    # inputsFrom — so a bump landing on a nixpkgs rev those aren't cached for yet
    # would have CI compiling a Haskell toolchain before validation even starts,
    # for tools the validation never calls. just + jq are cheap and always cached.
    #
    # No shellHook either: `default`'s installs git hooks, which is right for a
    # human entering the shell and pure noise on a runner that never commits.
    devShells.ci = pkgs.mkShell {
      packages = with pkgs; [jq just];
    };

    devShells.default = pkgs.mkShell {
      inputsFrom = [config.treefmt.build.devShell];
      shellHook = config.pre-commit.installationScript;
      packages = with pkgs; [
        git
        jq # `just validate` parses `nix eval --json` with it
        just
        nh
        nix-output-monitor
        nvd
      ];
    };
  };
}
