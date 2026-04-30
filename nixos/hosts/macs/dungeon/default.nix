{
  vars,
  lib,
  pkgs,
  ...
}: {
  imports = [
    ../../../modules/darwin/common.nix
    ../../../modules/darwin/homebrew.nix
    ../../../modules/darwin/home.nix
  ];

  networking.hostName = "dungeon";

  # Enable SSH (Remote Login) for remote access
  services.openssh.enable = true;

  # Server mode — prevent sleep when lid is closed (clamshell mode)
  #
  # PROBLEM:
  # This MacBook Pro (Apple Silicon M4 Pro) runs as a headless Docker server via
  # OrbStack with the lid closed 99% of the time. By default, macOS enters
  # "Clamshell Sleep" the moment the lid closes unless an external display is
  # attached. When the machine sleeps, OrbStack's Linux VM suspends, the Docker
  # socket becomes unresponsive (`docker ps` hangs), NFS mounts go stale, and
  # all containers go offline.
  #
  # WHY caffeinate AND power.sleep.* ARE NOT ENOUGH:
  # - `caffeinate -sdi` prevents idle/display/system sleep via software assertions,
  #   but macOS on Apple Silicon ignores ALL software sleep assertions for the
  #   hardware-level clamshell sleep event. pmset logs confirm:
  #     "Entering Sleep state due to 'Clamshell Sleep'"
  #   even with caffeinate running and power.sleep set to "never".
  # - `pmset standby 0 / hibernatemode 0` disable secondary sleep mechanisms but
  #   do not prevent the initial clamshell sleep trigger.
  #
  # THE FIX — `pmset -a disablesleep 1`:
  # This is an undocumented pmset flag that completely disables ALL sleep,
  # including clamshell sleep on Apple Silicon. It shows up in `pmset -g` as
  # `SleepDisabled 1`. This is set in the activation script below.
  #
  # We keep three layers of defense for robustness:
  #   1. power.sleep.* — nix-darwin's declarative pmset wrappers (idle sleep only)
  #   2. pmset -a disablesleep 1 — the critical fix for clamshell sleep (activation script)
  #   3. caffeinate daemon — belt-and-suspenders for idle sleep assertions
  #
  # If the machine still sleeps, a hardware HDMI dummy plug (~$8) is the nuclear
  # option — it fakes an external display so macOS enters normal clamshell mode.
  #
  # References:
  #   https://github.com/Moarram/wake (script built around disablesleep)
  #   https://www.macworld.com/article/673295/how-to-use-macbook-with-lid-closed-stop-closed-mac-sleeping.html
  #   https://github.com/waydabber/BetterDisplay (software dummy display alternative)
  #
  # WARNING: Reduced cooling with lid closed — ensure adequate ventilation.
  power.sleep.computer = "never";
  power.sleep.display = lib.mkForce "never";

  # caffeinate daemon — continuously asserts against idle/display/system sleep.
  # NOTE: This alone does NOT prevent clamshell sleep on Apple Silicon (see above).
  # Kept as a secondary measure alongside the pmset disablesleep override.
  # Must be plugged into a power source to stay awake with lid closed.
  #
  # Flags:
  #   -s  prevent system (idle) sleep while on AC power
  #   -d  prevent display sleep
  #   -i  prevent idle sleep regardless of power source
  launchd.daemons.prevent-sleep = {
    command = "/usr/bin/caffeinate -sdi";
    serviceConfig = {
      KeepAlive = true;
      RunAtLoad = true;
    };
  };

  # NFS mount for Unraid data share
  # Mirrors the NixOS VM mount at nixos/hosts/vms/home-lab/default.nix (192.168.1.2:/mnt/user/data)
  # Mount point matches SERVER_DATA_SHARE_MOUNT_POINT in the home-lab .env
  # macOS doesn't support fileSystems in nix-darwin, so we use a launchd daemon instead.
  # The daemon waits for the NFS server to be reachable, then mounts.
  # KeepAlive + exit-on-already-mounted ensures it remounts after network recovery.
  launchd.daemons.mount-unraid-data = {
    script = ''
      MOUNT_POINT="/Volumes/unraid-data"
      NFS_SERVER="${vars.networking.hosts.unraid.lan}"
      NFS_PATH="/mnt/user/data"

      # Create mount point if it doesn't exist
      /bin/mkdir -p "$MOUNT_POINT"

      # If already mounted, nothing to do
      if /sbin/mount | /usr/bin/grep -q "$MOUNT_POINT"; then
        exit 0
      fi

      # Wait for NFS server to be reachable (up to 60s)
      for i in $(seq 1 12); do
        if /sbin/ping -c 1 -W 1 "$NFS_SERVER" >/dev/null 2>&1; then
          break
        fi
        /bin/sleep 5
      done

      # Mount the NFS share
      # -o resvport: required on macOS for NFS (uses privileged source port)
      # -o vers=3: Unraid exports NFSv3 — macOS defaults to v4 which hangs
      # -o nolock: skip NFS locking — Unraid uses local_lock=none, and rpc.statd isn't available
      # -o soft: return errors on timeout rather than hanging indefinitely
      # -o intr: allow signals to interrupt hung operations
      # -o rw: read-write access for Docker container bind mounts
      /sbin/mount -t nfs -o resvport,vers=3,nolock,soft,intr,rw "$NFS_SERVER:$NFS_PATH" "$MOUNT_POINT"
    '';
    serviceConfig = {
      RunAtLoad = true;
      # Retry every 30s if the mount fails (e.g., server not yet up after reboot)
      KeepAlive = {
        SuccessfulExit = false;
      };
      # Don't restart too aggressively
      ThrottleInterval = 30;
      StandardOutPath = "/var/log/mount-unraid-data.log";
      StandardErrorPath = "/var/log/mount-unraid-data.log";
    };
  };

  # NFS mount for Fob offsite backup (Raspberry Pi via Tailscale)
  # Used by Kopia for offsite backups — not used by Docker containers.
  # Tailscale may not be connected at boot, so we retry more aggressively.
  launchd.daemons.mount-fob-backup = {
    script = ''
      MOUNT_POINT="/Volumes/fob-backup"
      NFS_SERVER="${vars.networking.hosts.fob.tailscale}"
      NFS_PATH="/mnt/mothership"

      # Create mount point if it doesn't exist
      /bin/mkdir -p "$MOUNT_POINT"

      # If already mounted, nothing to do
      if /sbin/mount | /usr/bin/grep -q "$MOUNT_POINT"; then
        exit 0
      fi

      # Wait for NFS server to be reachable (up to 120s — Tailscale may take time)
      for i in $(seq 1 24); do
        if /sbin/ping -c 1 -W 1 "$NFS_SERVER" >/dev/null 2>&1; then
          break
        fi
        /bin/sleep 5
      done

      # Mount the NFS share
      # -o resvport: required on macOS for NFS (uses privileged source port)
      # -o vers=3: use NFSv3 explicitly — macOS defaults to v4 which can hang
      # -o nolock: skip NFS locking — Fob doesn't run rpc.statd, and Kopia handles its own consistency
      # -o soft: return errors on timeout rather than hanging indefinitely
      # -o intr: allow signals to interrupt hung operations
      # -o rw: read-write access for backup writes
      /sbin/mount -t nfs -o resvport,vers=3,nolock,soft,intr,rw "$NFS_SERVER:$NFS_PATH" "$MOUNT_POINT"
    '';
    serviceConfig = {
      RunAtLoad = true;
      KeepAlive = {
        SuccessfulExit = false;
      };
      ThrottleInterval = 30;
      StandardOutPath = "/var/log/mount-fob-backup.log";
      StandardErrorPath = "/var/log/mount-fob-backup.log";
    };
  };

  # Healthchecks.io ping — signals that dungeon is alive and has network.
  # If this stops, healthchecks.io sends an alert (power outage, network down, etc.)
  launchd.daemons.healthcheck-ping = {
    serviceConfig = {
      ProgramArguments = [
        "/usr/bin/curl"
        "-fsS"
        "--retry"
        "3"
        vars.services.healthchecks.pingUrl
      ];
      StartInterval = vars.services.healthchecks.intervalSeconds;
      StandardOutPath = "/var/log/healthcheck-ping.log";
      StandardErrorPath = "/var/log/healthcheck-ping.log";
    };
  };

  # Deploy oMLX with dungeon-specific settings (8GB hot cache for M3 Pro 36GB)
  # See ~/Git/toolbox/dot/omlx/README.md for stow strategy explanation
  # Combined with home-lab-config deployment and power management
  # NOTE: Uses postActivation (not custom names) because nix-darwin only runs well-known activation script names.
  system.activationScripts.postActivation.text = ''
    set -euo pipefail  # Exit on error, undefined vars, and pipeline failures

    # Deploy oMLX dotfiles: base config + dungeon-specific overrides
    # settings.json is excluded from stow (via .stow-local-ignore) because it
    # contains host-specific cache sizes AND auth keys. Merged with jq instead.
    export PATH="${pkgs.stow}/bin:${pkgs.jq}/bin:$PATH"
    TOOLBOX="/Users/${vars.user.name}/Git/toolbox/dot"
    cd "$TOOLBOX"
    stow -R omlx

    # Merge base settings.json + dungeon cache overlay → ~/.omlx/settings.json
    # Write to a temp file first, then mv into place. This avoids truncating the
    # source if ~/.omlx/settings.json is a stale symlink pointing back to it,
    # and is atomic (the old file survives if jq fails).
    OMLX_SETTINGS="/Users/${vars.user.name}/.omlx/settings.json"
    jq -s '.[0] * .[1]' \
      "$TOOLBOX/omlx/.omlx/settings.json" \
      "$TOOLBOX/omlx-dungeon/.omlx/settings.json" \
      > "$OMLX_SETTINGS.tmp"
    mv -f "$OMLX_SETTINGS.tmp" "$OMLX_SETTINGS"

    echo "✓ oMLX configured for dungeon (hot_cache_max_size=8GB)"

    # Prevent clamshell sleep on Apple Silicon (lid-close with no external display).
    # See the detailed explanation in the power.sleep section above.
    #
    # nix-darwin doesn't expose these pmset settings declaratively, so we set them here.
    #   disablesleep 1  — undocumented pmset flag that prevents ALL sleep, including
    #                     the hardware-level clamshell sleep on Apple Silicon. This is
    #                     the critical setting — without it, closing the lid kills
    #                     OrbStack and all Docker containers. Shows as "SleepDisabled 1"
    #                     in `pmset -g`. See: https://github.com/Moarram/wake
    #   standby 0       — disable standby (deep sleep after prolonged idle)
    #   hibernatemode 0 — disable writing RAM to disk and sleeping
    #   autopoweroff 0  — disable auto power-off after prolonged standby
    # -a applies to all power sources (AC and battery).
    pmset -a disablesleep 1 standby 0 hibernatemode 0 autopoweroff 0

    # Create NFS mount points
    mkdir -p /Volumes/unraid-data
    mkdir -p /Volumes/fob-backup

    sudo -H -u "${vars.user.name}" mkdir -p "/Users/${vars.user.name}/home-lab-config"

    USER="${vars.user.name}"
    REPO_DIR="/Users/$USER/Git/home-lab"
    sudo -H -u "$USER" mkdir -p "/Users/$USER/Git"

    # Test SSH access to GitHub before attempting git operations
    # NOTE: ssh -T returns exit code 1 even on success, so we use || true and check output
    SSH_OUTPUT=$(sudo -H -u "$USER" ssh -o StrictHostKeyChecking=accept-new -T git@github.com 2>&1 || true)
    if echo "$SSH_OUTPUT" | grep -q "successfully authenticated"; then
      if [ ! -d "$REPO_DIR/.git" ]; then
        echo "Cloning home-lab repo..."
        sudo -H -u "$USER" git clone git@github.com:GregHilston/home-lab.git "$REPO_DIR"
      else
        echo "Pulling latest home-lab changes..."
        sudo -H -u "$USER" git -C "$REPO_DIR" pull --ff-only
      fi
    else
      echo ""
      echo "========================================================"
      echo "  WARNING: GitHub SSH authentication failed!"
      echo "  Could not clone/pull GregHilston/home-lab."
      echo ""
      echo "  SSH keys are either missing or not added to GitHub."
      echo "  See nixos/modules/darwin/README.md for initial setup."
      echo "========================================================"
      echo ""
      exit 1
    fi
  '';
}
