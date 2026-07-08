{
  vars,
  lib,
  pkgs,
  ...
}: let
  # NFS mounts on macOS: nix-darwin has no `fileSystems` support, so each share is a
  # launchd daemon that waits for the server to answer ping, then mounts NFSv3.
  # KeepAlive(SuccessfulExit=false) + the "already mounted? exit 0" guard means it
  # remounts after a network drop without thrashing. This helper holds the shared
  # retry/ping/mount logic; only the per-share fields below differ.
  mkNfsMountDaemon = {
    mountPoint,
    server,
    path,
    retries,
    logFile,
  }: {
    script = ''
      MOUNT_POINT="${mountPoint}"
      NFS_SERVER="${server}"
      NFS_PATH="${path}"

      # Create mount point if it doesn't exist
      /bin/mkdir -p "$MOUNT_POINT"

      # If already mounted, nothing to do
      if /sbin/mount | /usr/bin/grep -q "$MOUNT_POINT"; then
        exit 0
      fi

      # Wait for the NFS server to be reachable (${toString retries} tries × 5s)
      for i in $(seq 1 ${toString retries}); do
        if /sbin/ping -c 1 -W 1 "$NFS_SERVER" >/dev/null 2>&1; then
          break
        fi
        /bin/sleep 5
      done

      # Mount the NFS share. Flags (macOS NFSv3):
      #   resvport  privileged source port (required on macOS)
      #   vers=3    macOS defaults to v4, which hangs against these servers
      #   nolock    servers don't run rpc.statd; consistency handled elsewhere
      #   soft,intr return/interrupt on timeout instead of hanging indefinitely
      #   rw        read-write (Docker bind mounts / backup writes)
      /sbin/mount -t nfs -o resvport,vers=3,nolock,soft,intr,rw "$NFS_SERVER:$NFS_PATH" "$MOUNT_POINT"
    '';
    serviceConfig = {
      RunAtLoad = true;
      # Retry every 30s if the mount fails (e.g., server not yet up after reboot)
      KeepAlive = {
        SuccessfulExit = false;
      };
      ThrottleInterval = 30;
      StandardOutPath = logFile;
      StandardErrorPath = logFile;
    };
  };
in {
  imports = [
    ../../../modules/darwin/common.nix
    ../../../modules/darwin/homebrew.nix
    ../../../modules/darwin/home.nix
    ../../../modules/darwin/omlx.nix
    ../../../modules/darwin/ser2net.nix
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

  # NFS mount for Unraid data share (NFSv3 over LAN). Used by Docker container bind
  # mounts; mirrors the NixOS VM mount at hosts/vms/home-lab/default.nix and matches
  # SERVER_DATA_SHARE_MOUNT_POINT in the home-lab .env.
  launchd.daemons.mount-unraid-data = mkNfsMountDaemon {
    mountPoint = "/Volumes/unraid-data";
    server = vars.networking.hosts.unraid.lan;
    path = "/mnt/user/data";
    retries = 12; # ~60s — LAN server, usually up quickly
    logFile = "/var/log/mount-unraid-data.log";
  };

  # NFS mount for Fob offsite backup (Raspberry Pi over Tailscale). Used by Kopia for
  # offsite backups, not by Docker. Tailscale may be slow to connect at boot, so wait longer.
  launchd.daemons.mount-fob-backup = mkNfsMountDaemon {
    mountPoint = "/Volumes/fob-backup";
    server = vars.networking.hosts.fob.tailscale;
    path = "/mnt/mothership";
    retries = 24; # ~120s — Tailscale may take time to come up
    logFile = "/var/log/mount-fob-backup.log";
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

  # Detect & auto-heal stale NFS file handles (ESTALE) on the home-lab_nfs-* Docker volumes.
  # Runs as a USER agent (not a system daemon) so it inherits the GUI/OrbStack docker context.
  # Root cause + manual fix: home-lab/CLAUDE.md → "NFS Stale File Handle (ESTALE)".
  launchd.user.agents.nfs-stale-check = {
    serviceConfig = {
      ProgramArguments = [
        "/bin/bash"
        "/Users/${vars.user.name}/Git/home-lab/scripts/nfs-stale-check.sh"
      ];
      RunAtLoad = true;
      StartInterval = 300; # every 5 min — probe is cheap (a few `docker exec ls`)
      StandardOutPath = "/Users/${vars.user.name}/Library/Logs/nfs-stale-check.log";
      StandardErrorPath = "/Users/${vars.user.name}/Library/Logs/nfs-stale-check.log";
    };
  };

  # Deploy oMLX with dungeon-specific settings (8GB hot cache for M3 Pro 36GB).
  # The symlink + jq-merge + restart logic lives in modules/darwin/omlx.nix.
  services.omlxDeploy = {
    enable = true;
    cacheSize = "8GB";
  };

  # Dungeon-specific activation: ser2net dotfiles, clamshell-sleep prevention,
  # NFS mount points, and the home-lab repo clone/pull.
  # NOTE: Uses postActivation (not custom names) because nix-darwin only runs well-known activation script names.
  system.activationScripts.postActivation.text = ''
    set -euo pipefail  # Exit on error, undefined vars, and pipeline failures

    # Stow ser2net dotfiles (USB serial exposure for OrbStack containers).
    export PATH="${pkgs.stow}/bin:$PATH"
    TOOLBOX="/Users/${vars.user.name}/Git/toolbox/dot"
    cd "$TOOLBOX"
    stow -R --no-folding ser2net

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

  # ---------------------------------------------------------------------------
  # Monitoring exporters for the home-lab Prometheus/Grafana stack.
  # These run NATIVELY (not as containers) so they report the real Mac — a
  # containerised exporter only sees OrbStack's Linux VM. Prometheus scrapes them
  # over host.docker.internal, so they bind 0.0.0.0. Packages: ../../modules/darwin/homebrew.nix.
  # ---------------------------------------------------------------------------

  # Host metrics: CPU, filesystem, disk I/O, network, load, uptime + the battery
  # textfile collector (fed by bin/mac-battery-textfile.sh below).
  launchd.user.agents.node-exporter = {
    command = "/opt/homebrew/bin/node_exporter --web.listen-address=0.0.0.0:9100 --collector.textfile.directory=/Users/${vars.user.name}/.local/state/node_exporter";
    serviceConfig = {
      RunAtLoad = true;
      KeepAlive = true;
      StandardOutPath = "/Users/${vars.user.name}/Library/Logs/node-exporter.log";
      StandardErrorPath = "/Users/${vars.user.name}/Library/Logs/node-exporter.log";
    };
  };

  # Apple-Silicon metrics: CPU/GPU/ANE power, temperature, fan, RAM, utilization.
  # macmon's default serve port (9090) collides with Prometheus, so use 9101.
  launchd.user.agents.macmon = {
    command = "/opt/homebrew/bin/macmon serve --port 9101";
    serviceConfig = {
      RunAtLoad = true;
      KeepAlive = true;
      StandardOutPath = "/Users/${vars.user.name}/Library/Logs/macmon.log";
      StandardErrorPath = "/Users/${vars.user.name}/Library/Logs/macmon.log";
    };
  };

  # Native Glances web UI on the same port the old container used (61208), so the
  # Caddy @glances route + Homepage tile keep working but now show the real Mac.
  # If `glances -w` fails for missing web deps, reinstall glances with web support.
  launchd.user.agents.glances = {
    command = "/opt/homebrew/bin/glances -w --bind 0.0.0.0 --port 61208";
    serviceConfig = {
      RunAtLoad = true;
      KeepAlive = true;
      StandardOutPath = "/Users/${vars.user.name}/Library/Logs/glances.log";
      StandardErrorPath = "/Users/${vars.user.name}/Library/Logs/glances.log";
    };
  };

  # Battery % + power source (pmset) for node_exporter's textfile collector —
  # node_exporter has no battery collector on macOS, so we shell out every 60s.
  launchd.user.agents.mac-battery-textfile = {
    serviceConfig = {
      ProgramArguments = [
        "/bin/bash"
        "/Users/${vars.user.name}/Git/toolbox/bin/mac-battery-textfile.sh"
      ];
      RunAtLoad = true;
      StartInterval = 60;
      StandardOutPath = "/Users/${vars.user.name}/Library/Logs/mac-battery-textfile.log";
      StandardErrorPath = "/Users/${vars.user.name}/Library/Logs/mac-battery-textfile.log";
    };
  };

  # ---------------------------------------------------------------------------
  # Frigate object detection on the Apple Neural Engine.
  # Frigate runs in OrbStack's Linux VM, which can't reach the ANE — so the
  # detector (frigate-nvr/apple-silicon-detector) runs NATIVELY here and Frigate
  # connects from the container over ZMQ/TCP (config: detectors.type=zmq,
  # endpoint=tcp://host.docker.internal:5555). This moves the single biggest
  # CPU consumer (CPU inference was ~64% of Frigate's load) onto the Neural
  # Engine. Run in AUTO mode: Frigate ships the yolov9 model over ZMQ on connect.
  # Manual one-time install (not auto-cloned — see darwin-post-deploy.md):
  #   git clone https://github.com/frigate-nvr/apple-silicon-detector ~/Git/apple-silicon-detector
  #   cd ~/Git/apple-silicon-detector && /opt/homebrew/bin/python3.11 -m venv venv
  #   ./venv/bin/pip3 install -r requirements.txt
  launchd.user.agents.frigate-detector = {
    serviceConfig = {
      ProgramArguments = [
        "/Users/${vars.user.name}/Git/apple-silicon-detector/venv/bin/python3"
        "-u"
        "/Users/${vars.user.name}/Git/apple-silicon-detector/detector/zmq_onnx_client.py"
      ];
      WorkingDirectory = "/Users/${vars.user.name}/Git/apple-silicon-detector";
      RunAtLoad = true;
      KeepAlive = true;
      StandardOutPath = "/Users/${vars.user.name}/Library/Logs/frigate-detector.log";
      StandardErrorPath = "/Users/${vars.user.name}/Library/Logs/frigate-detector.log";
    };
  };
}
