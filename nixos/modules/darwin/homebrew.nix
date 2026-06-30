# Homebrew for the "media/server" Darwin hosts (dungeon, moria).
# Imports the shared baseline and adds host-class-specific extras. The oMLX
# launchd agent and the common brews/casks/taps live in homebrew-base.nix.
{...}: {
  imports = [./homebrew-base.nix];

  homebrew = {
    brews = [
      "go"
      "hugo"
      "ser2net" # Exposes USB serial devices over TCP for OrbStack containers

      # Runtime (needed by pi for npm: packages)
      "node"

      # Monitoring exporters — scraped by the home-lab Prometheus over
      # host.docker.internal. Native (not containers) so they report the real Mac,
      # not OrbStack's Linux VM. See launchd.user.agents in hosts/macs/dungeon.
      "node_exporter" # host CPU/disk/net/load/filesystem (:9100)
      "macmon" # Apple-Silicon temp/power/GPU/RAM via `macmon serve` (:9101)
      "glances" # native system-monitor web UI (:61208), replaces the container
    ];

    casks = [
      "google-chrome"
      "discord"
      "calibre"
      "orbstack"
      "shortcat"
      "tailscale-app"
      "1password-cli"

      # AI
      "claude"
      "lm-studio"
      "draw-things"

      # Other
      "flux-app"
      "steam"
      "godot"
    ];
  };
}
