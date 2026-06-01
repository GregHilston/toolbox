{
  vars,
  pkgs,
  lib,
  ...
}: {
  imports = [
    ../../../modules/darwin/common.nix
    ../../../modules/darwin/home.nix
  ];

  networking.hostName = "citadel";

  # --- Homebrew ---
  homebrew = {
    enable = true;

    onActivation = {
      autoUpdate = true;
      cleanup = "none"; # don't touch apps not declared here
      upgrade = true;
    };

    taps = [
      "nikitabobko/tap" # AeroSpace
    ];

    brews = [
      "stow"
      "tmux"
      "just"
      "pandoc"
      "gh"
    ];

    casks = [
      # Core
      "ghostty"
      "visual-studio-code"

      # Media
      "spotify"
      "vlc"

      # Dev
      "bruno"
      "db-browser-for-sqlite"
      "ngrok"

      # Productivity
      "obsidian"
      "raycast"
      "stats"
      "jordanbaird-ice"
      "aerospace"
    ];
  };

  # Override home-manager packages for this host
  home-manager.users.${vars.user.name} = {
    home.packages = lib.mkForce (with pkgs; [
      uv
      git
      ripgrep
      duckdb
      ffmpeg
      python3

      # Fonts
      nerd-fonts.jetbrains-mono
      jetbrains-mono
    ]);

    # Disable modules not needed on this host
    custom.programs.pi.enable = lib.mkForce false;
    custom.programs.opencode.enable = lib.mkForce false;

    # Disable mflux activation
    home.activation.install-mflux = lib.mkForce "";
  };
}
