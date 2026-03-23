{...}: {
  homebrew = {
    enable = true;

    onActivation = {
      autoUpdate = true;
      cleanup = "zap";
      upgrade = true;
    };

    taps = [
      "nikitabobko/tap" # AeroSpace
    ];

    casks = [
      # Core
      "1password"
      "alacritty"
      "ghostty"
      "firefox"
      "google-chrome"
      "visual-studio-code"

      # Communication
      "discord"
      "slack"
      "microsoft-onenote"

      # Media
      "spotify"
      "vlc"
      "calibre"

      # Dev
      "bruno"
      "docker"
      "dbeaver-community"
      "db-browser-for-sqlite"
      "postman"
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
      "anki"
      "flux"
      "steam"
      "godot"
    ];
  };
}
