{
  lib,
  pkgs,
  vars,
  ...
}: {
  imports = [
    ../../../modules/darwin/common.nix
    ../../../modules/darwin/homebrew.nix
    ../../../modules/darwin/home.nix
  ];

  networking.hostName = "moria";

  home-manager.users.${vars.user.name} = {
    # Moria-specific packages (Whisper for local transcription, Python for parakeet-mlx)
    home.packages = with pkgs; [
      whisper-ctranslate2
      ffmpeg
    ];

    imports = [./qwen-code.nix];
  };

  # Deploy oMLX with moria-specific settings (32GB hot cache for M4 Max 128GB)
  # See ~/Git/toolbox/dot/omlx/README.md for stow strategy explanation
  #
  # settings.json is excluded from stow (via .stow-local-ignore) because it
  # contains host-specific cache sizes AND auth keys that shouldn't be duplicated
  # into per-host stow packages. Instead we merge base + overlay with jq.
  system.activationScripts.postActivation.text = lib.mkBefore ''
    export PATH="${pkgs.stow}/bin:${pkgs.jq}/bin:$PATH"
    TOOLBOX="/Users/${vars.user.name}/Git/toolbox/dot"

    # Stow shared oMLX files (model_settings.json, stats.json, etc.)
    # --no-folding prevents stow from symlinking the .omlx/ directory itself
    # into the repo. Without it, oMLX writes (settings saves, cache, logs)
    # land directly in the git working tree.
    cd "$TOOLBOX"
    stow -R --no-folding omlx

    # Merge base settings.json + moria cache overlay → ~/.omlx/settings.json
    # Write to a temp file first, then mv into place. This avoids truncating the
    # source if ~/.omlx/settings.json is a stale symlink pointing back to it,
    # and is atomic (the old file survives if jq fails).
    OMLX_SETTINGS="/Users/${vars.user.name}/.omlx/settings.json"
    jq -s '.[0] * .[1]' \
      "$TOOLBOX/omlx/.omlx/settings.json" \
      "$TOOLBOX/omlx-moria/.omlx/settings.json" \
      > "$OMLX_SETTINGS.tmp"
    mv -f "$OMLX_SETTINGS.tmp" "$OMLX_SETTINGS"

    # Restart oMLX so it picks up the merged settings.json.
    # KeepAlive only restarts on crashes, not config changes.
    launchctl kickstart -k "gui/$(id -u ${vars.user.name})/org.nixos.omlx" 2>/dev/null || true

    echo "✓ oMLX configured for moria (hot_cache_max_size=32GB)"
  '';
}
