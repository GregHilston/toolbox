{...}: {
  homebrew = {
    enable = true;

    onActivation = {
      autoUpdate = true;
      cleanup = "check";
      upgrade = true;
    };

    taps = [
      "nikitabobko/tap" # AeroSpace
    ];

    casks = [
      # Core
      "ghostty"
      "firefox"
      "google-chrome"
      "visual-studio-code"

      # Communication
      "discord"
      "slack"

      # Media
      "spotify"
      "vlc"
      "calibre"

      # Dev
      "bruno"
      "docker"
      "dbeaver-community"
      "db-browser-for-sqlite"
      "ngrok"

      # Productivity
      "obsidian"
      "raycast"
      "stats"
      "bartender"
      "aerospace"

      # AI
      "claude"
      "lm-studio"
      "draw-things"

      # Other
      "bitwarden"
      "flux"
      "steam"
      "godot"
    ];
  };
}
