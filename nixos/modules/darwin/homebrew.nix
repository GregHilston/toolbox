{...}: {
  homebrew = {
    enable = true;

    onActivation = {
      autoUpdate = true;
      # "none" — don't touch packages not in this file. Change to "check" once
      # manually-installed brew drift has been cleaned up on this machine.
      cleanup = "none";
      upgrade = true;
    };

    taps = [
      "nikitabobko/tap" # AeroSpace
      {
        name = "jundot/omlx";
        clone_target = "https://github.com/jundot/omlx";
      } # omlx LLM inference server
    ];

    brews = [
      "stow"

      # CLI tools — managed here rather than nix for easier updates on macOS
      "tmux"
      "just"
      "pandoc"
      "gh"
      "go"
      "hugo"

      # AI / LLM
      "jundot/omlx/omlx"
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
      "docker-desktop"
      "orbstack"
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

      # Networking
      "tailscale-app"

      # Other
      "1password"
      "flux-app"
      "steam"
      "godot"
    ];
  };
}
