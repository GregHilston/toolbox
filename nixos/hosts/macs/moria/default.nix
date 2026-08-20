{
  lib,
  pkgs,
  vars,
  ...
}: {
  imports = [
    ../../../modules/darwin/common.nix
    ../../../modules/darwin/homebrew-server.nix
    ../../../modules/darwin/home.nix
    ../../../modules/darwin/omlx.nix
    # Launch Handy at login so the Caps-Lock-hold → F18 dictation hotkey works
    # without opening the app by hand.
    ../../../modules/darwin/handy.nix
    # PI WEB — supervise pi sessions from a browser. moria only: it is the
    # 128GB box and already runs oMLX, so sessions and inference stay together.
    ../../../modules/darwin/pi-web.nix
  ];

  networking.hostName = "moria";

  # Display sleep timeout (30 minutes instead of default 5)
  power.sleep.display = lib.mkForce 30;

  # Gaming (moria-only; kept out of the shared homebrew-server.nix so the headless
  # dungeon server doesn't pull them in). nix-darwin merges these into the
  # casks list from modules/darwin/homebrew-server.nix.
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
    # Moria-specific packages: whisper for local transcription, ffmpeg to extract
    # audio from video first. The comment here used to also claim a Python for
    # parakeet-mlx — that was for bin/audio-transcript.py, which now lives in
    # roger (roger/audio/transcribe.py) and brings its own environment.
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

  # Keep pi's Reddit session cookie current by copying it out of Firefox.
  #
  # Reddit expires it every few days and offers no refresh-token flow, so this
  # cannot renew a session — only copy one you already have. It no-ops while the
  # existing cookie still authenticates, and notifies if Firefox cannot supply a
  # working one. See bin/reddit-cookie-sync.sh for the full tradeoff.
  #
  # A user agent, not postActivation: it needs the network and the user's own
  # Firefox profile, neither of which root-at-activation should be touching.
  launchd.user.agents.reddit-cookie-sync = {
    serviceConfig = {
      ProgramArguments = [
        "/bin/bash"
        "/Users/${vars.user.name}/Git/toolbox/bin/reddit-cookie-sync.sh"
      ];
      RunAtLoad = true;
      StartInterval = 86400; # daily; the cookie lasts a few days
      StandardOutPath = "/Users/${vars.user.name}/Library/Logs/reddit-cookie-sync.log";
      StandardErrorPath = "/Users/${vars.user.name}/Library/Logs/reddit-cookie-sync.log";
    };
  };

  # PI WEB deploys its config here; the service itself is installed once with
  # `just pi-web-setup`. See modules/darwin/pi-web.nix for why nix does not own
  # its launchd agents.
  custom.programs.piWeb.enable = true;
}
