{
  vars,
  lib,
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

  # Server mode - prevent sleep when lid is closed
  power.sleep.computer = "never";
  power.sleep.display = lib.mkForce "never";

  # LaunchDaemon that continuously prevents sleep (including lid-close).
  # NOTE: Must be plugged into a power source to stay awake with lid closed.
  #
  # caffeinate flags:
  #   -s  prevent system (idle) sleep while on AC power
  #   -d  prevent display sleep — critical for clamshell (lid-closed) mode because
  #       macOS treats lid-close as a display sleep event that cascades into full
  #       system sleep; blocking it keeps OrbStack and Docker alive
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

  # Ensure the home-lab-config directory exists
  # Auto-clone or pull the home-lab repo (requires SSH keys configured for GitHub)
  # NOTE: Uses postActivation (not custom names) because nix-darwin only runs well-known activation script names.
  # NOTE: sudo -H sets HOME to the target user's home dir (otherwise HOME stays as /var/root
  #       and SSH can't find keys in ~/.ssh)
  system.activationScripts.postActivation.text = lib.mkBefore ''
    set -euo pipefail  # Exit on error, undefined vars, and pipeline failures

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
