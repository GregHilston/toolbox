{vars, ...}: {
  # Launch omlx LLM inference server at login so pi and other tools can connect.
  # Runs as a user agent (not a system daemon) so it has access to ~/models and ~/.omlx/.
  launchd.user.agents.omlx = {
    command = "/opt/homebrew/bin/omlx serve";
    serviceConfig = {
      RunAtLoad = true;
      KeepAlive = true;
      StandardOutPath = "/Users/${vars.user.name}/Library/Logs/omlx.log";
      StandardErrorPath = "/Users/${vars.user.name}/Library/Logs/omlx.log";
    };
  };

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
      "pi-coding-agent"
      "qwen-code"
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
      "jordanbaird-ice"
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
