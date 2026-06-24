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
      "ser2net" # Exposes USB serial devices over TCP for OrbStack containers

      # CLI tools — managed here rather than nix for easier updates on macOS
      "tmux"
      "just"
      "pandoc"
      "gh"
      "go"
      "hugo"

      # Runtime (needed by pi for npm: packages)
      "node"

      # AI / LLM
      "jundot/omlx/omlx"
      "pi-coding-agent"

      # Monitoring exporters — scraped by the home-lab Prometheus over
      # host.docker.internal. Native (not containers) so they report the real Mac,
      # not OrbStack's Linux VM. See launchd.user.agents in hosts/macs/dungeon.
      "node_exporter" # host CPU/disk/net/load/filesystem (:9100)
      "macmon" # Apple-Silicon temp/power/GPU/RAM via `macmon serve` (:9101)
      "glances" # native system-monitor web UI (:61208), replaces the container
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

      # Drivers
      "displaylink"

      # Other
      "1password"
      "1password-cli"
      "flux-app"
      "steam"
      "godot"
    ];
  };
}
