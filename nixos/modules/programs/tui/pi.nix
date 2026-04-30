{
  config,
  lib,
  pkgs,
  ...
}: let
  cfg = config.custom.programs.pi;
in {
  options.custom.programs.pi = {
    enable = lib.mkEnableOption "pi (pi-mono coding agent)";

    defaultModel = lib.mkOption {
      type = lib.types.str;
      default = "Qwen3.6-35B-A3B-8bit";
      description = "Default model to use";
    };

    # Packages installed via `pi install`. Pi resolves these at runtime.
    # Git-based packages are cloned to ~/.pi/agent/git/; npm packages go to
    # the global node_modules. Local extensions (plan-mode) live in
    # ~/.pi/agent/extensions/ managed by stow from dot/pi/.
    packages = lib.mkOption {
      type = lib.types.listOf lib.types.str;
      default = [
        # Rust-powered frecency-ranked, fuzzy, git-aware file search
        # https://github.com/dmtrKovalenko/fff
        "npm:@ff-labs/pi-fff"

        # Context management: context-projection (hides stale tool output),
        # context-overflow (proactive compaction), custom-compaction, subagents
        # https://github.com/n-r-w/pi-agent-suite
        "npm:pi-agent-suite"

        # Read-before-write enforcement, directory containment, work modes
        # https://github.com/galatolofederico/moonpi
        "https://github.com/galatolofederico/moonpi"
      ];
      description = "Pi packages to declare in settings.json";
    };
  };

  config = lib.mkIf cfg.enable {
    # models.json is managed by stow + op inject (dot/pi/.pi/agent/models.json.tpl).
    # Run `just secrets` to generate it from 1Password, then stow deploys it.

    home.file.".pi/agent/settings.json" = {
      text = builtins.toJSON {
        defaultProvider = "omlx";
        defaultModel = cfg.defaultModel;
        lastChangelogVersion = "0.67.6";
        packages = cfg.packages;
      };
    };

    # Install pi packages (npm/git) on activation. Pi declares packages in
    # settings.json but the actual npm globals and git clones need `pi install`.
    # This runs after writeBoundary so settings.json is already in place.
    # Each install is idempotent — pi skips already-installed packages.
    home.activation.installPiPackages = lib.hm.dag.entryAfter ["writeBoundary"] ''
      if command -v pi &>/dev/null; then
        ${builtins.concatStringsSep "\n        " (map (pkg: ''pi install "${pkg}" 2>/dev/null || true'') cfg.packages)}
        echo "✓ Pi packages installed"
      fi
    '';
  };
}
