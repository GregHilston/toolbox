# Homebrew for the "media/server" Darwin hosts (dungeon, moria).
# Imports the shared baseline and adds host-class-specific extras. The oMLX
# launchd agent and the common brews/casks/taps live in homebrew-base.nix.
{...}: {
  imports = [./homebrew-base.nix];

  homebrew = {
    brews = [
      "go"
      "hugo"

      # Runtime (needed by pi for npm: packages)
      "node"

      # Monitoring exporters — scraped by the home-lab Prometheus over
      # host.docker.internal. Native (not containers) so they report the real Mac,
      # not OrbStack's Linux VM. See launchd.user.agents in hosts/macs/dungeon.
      "node_exporter" # host CPU/disk/net/load/filesystem (:9100)
      "macmon" # Apple-Silicon temp/power/GPU/RAM via `macmon serve` (:9101)
      "glances" # native system-monitor web UI (:61208), replaces the container

      # Tier-1 backup engine, driven by the backup-tier1 launchd agent in
      # hosts/macs/dungeon. Deliberately on the whole server class rather than dungeon
      # alone: restic is also the *restore* tool, and the one machine you cannot count on
      # having during a restore is the one that was being backed up.
      "restic"
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
