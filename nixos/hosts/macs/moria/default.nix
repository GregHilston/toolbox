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

  # Gaming (moria-only; kept out of the shared homebrew.nix so the headless
  # dungeon server doesn't pull them in). nix-darwin merges these into the
  # casks list from modules/darwin/homebrew.nix.
  #   crossover — run Windows keyboard/mouse games natively (Wine + GPTK).
  #               Whisky is discontinued (Apr 2025); CrossOver is the path.
  #   moonlight — stream games in (from the Steam Deck via Sunshine, or from
  #               the desktop over Tailscale). Native Apple-Silicon Metal client.
  # Note: both apps' state (CrossOver bottles, Moonlight host pairing) is
  # runtime config, not declarative — same as oMLX model downloads.
  homebrew.casks = [
    "crossover"
    "moonlight"
  ];

  home-manager.users.${vars.user.name} = {
    # Moria-specific packages (Whisper for local transcription, Python for parakeet-mlx)
    home.packages = with pkgs; [
      whisper-ctranslate2
      ffmpeg
    ];
  };

  # Deploy oMLX with moria-specific settings (32GB hot cache for M4 Max 128GB).
  # The symlink + jq-merge + restart logic lives in modules/darwin/omlx.nix.
  services.omlxDeploy = {
    enable = true;
    cacheSize = "32GB";
  };
}
