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
    ../../../modules/darwin/omlx.nix
  ];

  networking.hostName = "moria";

  # Display sleep timeout (30 minutes instead of default 5)
  power.sleep.display = lib.mkForce 30;

  home-manager.users.${vars.user.name} = {
    # Moria-specific packages (Whisper for local transcription, Python for parakeet-mlx)
    home.packages = with pkgs; [
      whisper-ctranslate2
      ffmpeg
    ];
  };

  # Deploy oMLX with moria-specific settings (32GB hot cache for M4 Max 128GB).
  # The stow + jq-merge + restart logic lives in modules/darwin/omlx.nix.
  services.omlxDeploy = {
    enable = true;
    cacheSize = "32GB";
  };
}
