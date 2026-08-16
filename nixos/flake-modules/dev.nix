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
  }: let
    # This flake lives in nixos/, but git's root — and so pre-commit's working
    # directory — is the toolbox repo root one level up. Nothing bridges that gap
    # for us, and until these wrappers existed neither hook could run at all:
    #
    #   * `nix flake check` from the repo root finds no flake there.
    #   * treefmt's wrapper hardcodes `--tree-root-file=flake.nix` and gives up with
    #     "could not find [flake.nix] in /Users/…/toolbox".
    #
    # Both failed on every commit and every push. It went unnoticed because the
    # hooks are only installed by entering the dev shell, and the repo still had
    # working hand-written ones left over from the deleted scripts/install-hooks.sh
    # sitting in .git/hooks — so anyone who never ran `nix develop` saw no problem,
    # and anyone who did had their working hooks replaced by broken ones.
    #
    # `gitBin`, not `git`: a `let` binding outranks `with pkgs;`, so naming this
    # `git` would silently turn the `git` in the devShell's package list below into
    # this string, and mkShell would try to source the binary as a setup hook.
    gitBin = "${pkgs.git}/bin/git";

    # pre-commit passes filenames relative to the git root, so make them absolute
    # BEFORE changing directory — otherwise they resolve against nixos/ and treefmt
    # is handed paths that do not exist.
    treefmtHook = pkgs.writeShellScript "treefmt-hook" ''
      set -euo pipefail
      root=$(${gitBin} rev-parse --show-toplevel)
      files=()
      for f in "$@"; do files+=("$root/$f"); done
      cd "$root/nixos"
      exec ${config.treefmt.build.wrapper}/bin/treefmt \
        --fail-on-change --no-cache "''${files[@]}"
    '';

    # `nix` is put on PATH by /etc/zshrc and /etc/bashrc, which a GUI git client
    # (VS Code's SCM pane, Fork, Tower) never sources — so a bare `nix` here dies
    # with "command not found" from anything that isn't a terminal.
    #
    # The profile path rather than `${pkgs.nix}/bin/nix`: these Macs run Determinate
    # Nix with nix-darwin's `nix.enable = false`, so pinning nixpkgs' nix would run a
    # client the daemon does not match. It is also the stable-path rule from
    # dot/README.md — /nix/var/nix/profiles/... survives a GC, a store path may not.
    flakeCheckHook = pkgs.writeShellScript "flake-check-hook" ''
      set -euo pipefail
      export PATH="/nix/var/nix/profiles/default/bin:$PATH"
      cd "$(${gitBin} rev-parse --show-toplevel)/nixos"
      exec nix flake check
    '';
  in {
    pre-commit.settings.hooks = {
      treefmt = {
        # No `package`: upstream reads it only to build the default `entry`, which
        # the line below replaces, so setting it would imply a control it no longer
        # has — and the wrapper reaches for the same derivation directly.
        enable = true;
        entry = "${treefmtHook}";
        # Only the files the formatters actually handle. Left unset (the default),
        # pre-commit hands treefmt *every* staged file — README.md, .github/*.yml,
        # dot/… — each one outside the tree root treefmt is about to establish.
        #
        # `.nix` because treefmt.nix enables only alejandra, statix and deadnix. Add
        # a formatter for another filetype there and widen this too, or the hook
        # quietly stops covering it (`nix flake check` still would).
        files = "^nixos/.*\\.nix$";
      };

      flake-check = {
        enable = true;
        name = "nix flake check";
        entry = "${flakeCheckHook}";
        pass_filenames = false;
        # A push that only touches dot/ or bin/ cannot break the flake, and this
        # check is minutes, not seconds.
        files = "^nixos/";
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
