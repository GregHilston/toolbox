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

  home-manager.users.${vars.user.name} = {
    # Disable modules not needed on this host
    custom.programs.pi.enable = lib.mkForce false;
    custom.programs.opencode.enable = lib.mkForce false;

    # Disable mflux activation
    home.activation.install-mflux = lib.mkForce "";
  };
}
