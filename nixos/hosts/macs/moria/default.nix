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
  system.activationScripts.postActivation.text = lib.mkBefore ''
    # Ensure stow is available
    export PATH="${pkgs.stow}/bin:$PATH"

    # Deploy oMLX dotfiles: base config + moria-specific overrides
    cd "/Users/${vars.user.name}/Git/toolbox/dot"
    stow omlx omlx-moria

    echo "✓ oMLX configured for moria (hot_cache_max_size=32GB)"
  '';
}
