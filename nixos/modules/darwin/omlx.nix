{
  lib,
  vars,
  ...
}: {
  # Activation script for oMLX model setup on Darwin hosts
  # Creates model variant symlinks (e.g., Qwen3.6-35B-A3B-8bit-long-context → Qwen3.6-35B-A3B-8bit)
  # Allows model_settings.json to define separate configurations without duplicating model weights.
  # See: https://github.com/jundot/omlx/issues/341#issuecomment-4202459307

  system.activationScripts.postActivation.text = lib.mkAfter ''
    # Create oMLX model variant symlinks for multi-configuration support.
    # Models are stored in ~/Git/toolbox/dot/omlx/.omlx/models (per .stow-local-ignore)
    # and accessed directly by oMLX via settings.json model_dir configuration.
    # See: https://github.com/jundot/omlx/issues/341#issuecomment-4202459307
    MODELS_DIR="/Users/${vars.user.name}/Git/toolbox/dot/omlx/.omlx/models"
    if [ -d "$MODELS_DIR" ]; then
      # Qwen3.6-35B-A3B-8bit-long-context: extended context (1M tokens) for long-form analysis
      # Only create if source exists and target doesn't
      if [ -d "$MODELS_DIR/Qwen3.6-35B-A3B-8bit" ] && [ ! -e "$MODELS_DIR/Qwen3.6-35B-A3B-8bit-long-context" ]; then
        ln -s Qwen3.6-35B-A3B-8bit "$MODELS_DIR/Qwen3.6-35B-A3B-8bit-long-context"
        echo "✓ Created model variant symlink: Qwen3.6-35B-A3B-8bit-long-context"
      fi
    fi
  '';
}
