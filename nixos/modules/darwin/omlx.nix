{
  config,
  lib,
  pkgs,
  vars,
  ...
}: let
  cfg = config.services.omlxDeploy;
  user = vars.user.name;
  host = config.networking.hostName;

  modelDir = "/Users/${user}/Git/toolbox/dot/omlx/.omlx/models";

  # Per-host oMLX settings overlay, generated from this host's cacheSize and
  # user. Deep-merged (jq) onto the shared base settings.json during activation.
  # This replaces the old per-host dot/omlx-<host> stow packages; the model
  # block also fixes the base tpl's hardcoded username (e.g. citadel).
  settingsOverlay = pkgs.writeText "omlx-settings-overlay-${host}.json" (builtins.toJSON {
    cache = {
      enabled = true;
      ssd_cache_dir = "/Users/${user}/.omlx/kv-cache";
      ssd_cache_max_size = "auto";
      hot_cache_max_size = cfg.cacheSize;
      initial_cache_blocks = 256;
    };
    model = {
      model_dirs = [modelDir];
      model_dir = modelDir;
    };
  });
in {
  options.services.omlxDeploy = {
    enable = lib.mkEnableOption ''
      oMLX dotfile deployment on this Darwin host: stow the shared oMLX package,
      merge the base settings.json with the per-host omlx-<host> overlay via jq,
      and restart the launchd agent so it picks up the new settings
    '';

    cacheSize = lib.mkOption {
      type = lib.types.str;
      example = "8GB";
      description = ''
        Hot-cache size (hot_cache_max_size) for this host. This is authoritative:
        it is baked into the nix-generated settings overlay that is jq-merged onto
        the base settings.json during activation.
      '';
    };
  };

  config = {
    # Activation scripts for oMLX on Darwin hosts.
    #
    # nix-darwin concatenates every postActivation.text fragment into ONE bash
    # script, so ordering is controlled with mkBefore/mkAfter:
    #   * mkBefore — deploy settings.json early, before host-specific blocks
    #     (pmset, NFS, repo clones) that may depend on a running oMLX.
    #   * mkAfter  — create model-variant symlinks last, after deploy.
    system.activationScripts.postActivation.text = lib.mkMerge [
      # ── Deploy: stow + jq settings merge + agent restart (shared across hosts)
      (lib.mkIf cfg.enable (lib.mkBefore ''
        # Deploy oMLX dotfiles: shared base config + this host's overlay.
        # settings.json is excluded from stow (via .stow-local-ignore) because it
        # contains host-specific cache sizes AND auth keys; we merge with jq instead.
        # See ~/Git/toolbox/dot/omlx/README.md for the stow strategy explanation.
        export PATH="${pkgs.stow}/bin:${pkgs.jq}/bin:$PATH"
        TOOLBOX="/Users/${user}/Git/toolbox/dot"

        # --no-folding prevents stow from symlinking the .omlx/ directory itself
        # into the repo. Without it, oMLX writes (settings saves, cache, logs)
        # land directly in the git working tree.
        cd "$TOOLBOX"
        stow -R --no-folding omlx

        # Merge base settings.json + this host's nix-generated overlay →
        # ~/.omlx/settings.json. Write to a temp file first, then mv into place:
        # avoids truncating the source if ~/.omlx/settings.json is a stale symlink
        # pointing back to it, and is atomic (the old file survives if jq fails).
        OMLX_SETTINGS="/Users/${user}/.omlx/settings.json"
        jq -s '.[0] * .[1]' \
          "$TOOLBOX/omlx/.omlx/settings.json" \
          ${settingsOverlay} \
          > "$OMLX_SETTINGS.tmp"
        mv -f "$OMLX_SETTINGS.tmp" "$OMLX_SETTINGS"

        # Restart oMLX so it picks up the merged settings.json.
        # KeepAlive only restarts on crashes, not config changes.
        launchctl kickstart -k "gui/$(id -u ${user})/org.nixos.omlx" 2>/dev/null || true

        echo "✓ oMLX configured for ${host} (hot_cache_max_size=${cfg.cacheSize})"
      ''))

      # ── Model-variant symlinks for multi-configuration support.
      # Creates e.g. Qwen3.6-35B-A3B-8bit-long-context → Qwen3.6-35B-A3B-8bit so
      # model_settings.json can define separate configs without duplicating weights.
      # See: https://github.com/jundot/omlx/issues/341#issuecomment-4202459307
      (lib.mkAfter ''
        # Models live in ~/Git/toolbox/dot/omlx/.omlx/models (per .stow-local-ignore)
        # and are accessed directly by oMLX via settings.json model_dir.
        MODELS_DIR="/Users/${user}/Git/toolbox/dot/omlx/.omlx/models"
        if [ -d "$MODELS_DIR" ]; then
          # Qwen3.6-35B-A3B-8bit-long-context: extended context (1M tokens).
          # Only create if source exists and target doesn't.
          if [ -d "$MODELS_DIR/Qwen3.6-35B-A3B-8bit" ] && [ ! -e "$MODELS_DIR/Qwen3.6-35B-A3B-8bit-long-context" ]; then
            ln -s Qwen3.6-35B-A3B-8bit "$MODELS_DIR/Qwen3.6-35B-A3B-8bit-long-context"
            echo "✓ Created model variant symlink: Qwen3.6-35B-A3B-8bit-long-context"
          fi
        fi
      '')
    ];
  };
}
