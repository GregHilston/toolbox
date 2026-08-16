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
    ../../../modules/darwin/homebrew-server.nix
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

  # roger's daily digest email.
  #
  # This lives on dungeon, not moria, because everything roger needs is here: roger-redis,
  # the ~/Git/notes vault mount, the credentials dir, and the oMLX the compose stack points
  # at. It replaces `com.roger.digest.greg`, a hand-written (non-nix) agent on moria that
  # had drifted into failing every run — placeholder vault path, a dead LM Studio endpoint,
  # a model id oMLX does not serve, and no Redis on that host. launchctl reported
  # last_exit=1 and nothing surfaced it, which is exactly the failure mode nix-managing it
  # prevents. The script runs the digest INSIDE the compose stack so there is no second
  # copy of the config left to drift. See home-lab/scripts/roger-digest.sh.
  launchd.user.agents.roger-digest-greg = {
    serviceConfig = {
      ProgramArguments = [
        "/bin/bash"
        "/Users/${vars.user.name}/Git/home-lab/scripts/roger-digest.sh"
        "greg"
      ];
      # Daily at 05:30. Deliberately NOT RunAtLoad: this sends a real email, so an
      # activation or a reboot must not fire one.
      StartCalendarInterval = [
        {
          Hour = 5;
          Minute = 30;
        }
      ];
      StandardOutPath = "/Users/${vars.user.name}/Library/Logs/roger-digest-greg.log";
      StandardErrorPath = "/Users/${vars.user.name}/Library/Logs/roger-digest-greg.log";
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

  # Detect mains power loss/restoration, alert via Pushover, and Wake-on-LAN Unraid back
  # up once power returns. Detection works by probing the PoE cameras, which are
  # deliberately NOT on battery backup — so their reachability IS the mains signal.
  # Deliberately a plain launchd agent rather than a Grafana rule: Grafana and Prometheus
  # are containers inside OrbStack, exactly the stack most likely to be degraded during a
  # power event. This depends on nothing but the network.
  # Full topology + signal ladder: home-lab/docs/power-outage.md.
  launchd.user.agents.power-watch = {
    serviceConfig = {
      ProgramArguments = [
        "/bin/bash"
        "/Users/${vars.user.name}/Git/home-lab/scripts/power-watch.sh"
      ];
      RunAtLoad = true;
      # Every 60s. Far tighter than nfs-stale-check's 5 min because the whole point is to
      # catch the outage while there is still battery left to act on; the probe is two TCP
      # connects. A 2-run confirm streak means an edge is declared ~2 min after the event.
      StartInterval = 60;
      StandardOutPath = "/Users/${vars.user.name}/Library/Logs/power-watch.log";
      StandardErrorPath = "/Users/${vars.user.name}/Library/Logs/power-watch.log";
    };
  };

  # Detect drift between ProtonVPN's forwarded port and Transmission's peer-port, and
  # re-run the sync that should have run on its own.
  #
  # gluetun's up-command pages when it RUNS AND FAILS. It cannot cover the up-command not
  # running at all — nothing failed, so nothing alerts, while Transmission listens on a port
  # Proton no longer forwards and receives no inbound peers. Confirmed 2026-08-13: a gluetun
  # restart stranded the netns members, the sync failed against an unreachable RPC, and
  # Proton then handed back THE SAME PORT — so the up-command never fired again and the
  # staleness had nothing watching it.
  #
  # 15 min, not 5: the condition is silent-but-not-urgent (inbound peers only), the probe
  # costs two `docker exec`s, and the script itself confirms drift over 2 consecutive runs
  # before acting — so a real drift is healed within ~30 min while a reconnect's brief,
  # legitimate mismatch is never mistaken for one.
  # Rationale + failure modes: home-lab/docs/runbooks/proton-port-sync-failed.md.
  launchd.user.agents.port-sync-check = {
    serviceConfig = {
      ProgramArguments = [
        "/bin/bash"
        "/Users/${vars.user.name}/Git/home-lab/scripts/port-sync-check.sh"
      ];
      RunAtLoad = true;
      StartInterval = 900;
      StandardOutPath = "/Users/${vars.user.name}/Library/Logs/port-sync-check.log";
      StandardErrorPath = "/Users/${vars.user.name}/Library/Logs/port-sync-check.log";
    };
  };

  # Detect Frigate's GenAI descriptions being silently down.
  #
  # This is invisible to every monitoring layer we have: object detection is unaffected
  # (yolov9-t runs on the ANE), no container restarts, no HTTP probe moves, no cAdvisor
  # metric changes. Frigate looks perfectly healthy while writing no descriptions.
  # home-lab/docs/runbooks/frigate-genai-down.md said to build this "if it recurs" — it
  # recurred on 2026-08-16, when a `brew upgrade` left oMLX running a deleted bundle and
  # every GenAI request 409'd on a cached model-load failure. It was found days later by
  # accident, reading an unrelated log.
  #
  # One real vision round-trip through oMLX; Pushover on two consecutive failures.
  # Read-only by design — it never restarts oMLX, because an auto-heal would mask exactly
  # the recurring upgrade bug it exists to surface.
  launchd.user.agents.frigate-genai-check = {
    serviceConfig = {
      ProgramArguments = [
        "/bin/bash"
        "/Users/${vars.user.name}/Git/home-lab/scripts/frigate-genai-check.sh"
      ];
      RunAtLoad = true;
      # Every 30 min. Far looser than port-sync-check's 15 min: a missing description is
      # not urgent, and each run costs a real VLM inference that competes with Frigate's
      # own GenAI calls for the same ~28GB Metal ceiling.
      StartInterval = 1800;
      StandardOutPath = "/Users/${vars.user.name}/Library/Logs/frigate-genai-check.log";
      StandardErrorPath = "/Users/${vars.user.name}/Library/Logs/frigate-genai-check.log";
    };
  };

  # Detect & auto-heal a gluetun tunnel that is broken while Docker insists it is healthy.
  #
  # Incident 2026-08-14: a mains blip took the WAN down; gluetun rode it out by cycling
  # Proton servers and 25 min later was still resolving nothing, while reporting
  # health=healthy FailingStreak=0 RestartCount=0. Its healthcheck runs every 5s with
  # retries=3, but the internal VPN loop keeps partially recovering, so the failing streak
  # flapped 0->2 and never latched at 3. Nothing alerted: these services have no HTTP front
  # door for blackbox, so the whole VPN stack was silently dead for 45 minutes. It then
  # recurred ~26h later. Docker's health status is not a usable signal for this fault.
  #
  # The script therefore probes FUNCTION from inside the netns members, asking two
  # independent questions — can it reach a fixed IP (no DNS anywhere), and can it resolve a
  # name. The pair discriminates a DNS wedge from a dead tunnel from a stranded namespace,
  # which need different fixes. Rationale: home-lab/docs/runbooks/gluetun-dns-wedge.md.
  #
  # 5 min, matching nfs-stale-check: the probe is a few `docker exec`s, and the script
  # confirms a fault over 2 consecutive runs before restarting anything — so a real wedge is
  # healed within ~10 min while gluetun's legitimate few-second gaps mid-server-switch are
  # never mistaken for one. A 30-min cooldown stops a restart loop when Proton is at fault.
  launchd.user.agents.gluetun-health-check = {
    serviceConfig = {
      ProgramArguments = [
        "/bin/bash"
        "/Users/${vars.user.name}/Git/home-lab/scripts/gluetun-health-check.sh"
      ];
      RunAtLoad = true;
      StartInterval = 300;
      StandardOutPath = "/Users/${vars.user.name}/Library/Logs/gluetun-health-check.log";
      StandardErrorPath = "/Users/${vars.user.name}/Library/Logs/gluetun-health-check.log";
    };
  };

  # Deploy oMLX with dungeon-specific settings (8GB hot cache for M3 Pro 36GB).
  # The symlink + jq-merge + restart logic lives in modules/darwin/omlx.nix.
  services.omlxDeploy = {
    enable = true;
    cacheSize = "8GB";
  };

  # Dungeon-specific activation: ser2net dotfiles, clamshell-sleep prevention,
  # and NFS mount points.
  # NOTE: Uses postActivation (not custom names) because nix-darwin only runs well-known activation script names.
  #
  # Wrapped in a subshell for two reasons. nix-darwin concatenates every
  # module's postActivation.text into ONE bash script, so a bare
  # `set -euo pipefail` here would silently impose those options on every
  # fragment ordered after this one (modules/darwin/omlx.nix's mkAfter block,
  # modules/darwin/common.nix's defaults) — none of which were written for
  # them. And with `set -e` inside a shared script, any failure below would
  # abort those fragments too. The subshell scopes the options and the `||`
  # turns a failure into a warning, so a broken step here can't take the rest
  # of activation down with it.
  system.activationScripts.postActivation.text = ''
    (
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
    ) || echo "WARNING: dungeon post-activation block failed (see above); continuing."
  '';

  # Keep ~/Git/home-lab checked out and current. dungeon runs
  # scripts/nfs-stale-check.sh out of that repo (see the watchdog agent below),
  # so it has to exist on disk.
  #
  # This is a user agent rather than part of postActivation on purpose: as the
  # user it has the ssh-agent, so the old `sudo -H -u` trampoline and the SSH
  # pre-flight probe that guarded it are both gone, and a GitHub auth failure
  # can no longer abort a `darwin-rebuild switch`. Runs at login and every 6h.
  launchd.user.agents.home-lab-sync = {
    serviceConfig = {
      ProgramArguments = [
        "/bin/bash"
        "/Users/${vars.user.name}/Git/toolbox/bin/home-lab-sync.sh"
      ];
      RunAtLoad = true;
      StartInterval = 21600; # 6h
      StandardOutPath = "/Users/${vars.user.name}/Library/Logs/home-lab-sync.log";
      StandardErrorPath = "/Users/${vars.user.name}/Library/Logs/home-lab-sync.log";
    };
  };

  # ---------------------------------------------------------------------------
  # Monitoring exporters for the home-lab Prometheus/Grafana stack.
  # These run NATIVELY (not as containers) so they report the real Mac — a
  # containerised exporter only sees OrbStack's Linux VM. Prometheus scrapes them
  # over host.docker.internal, so they bind 0.0.0.0. Packages: ../../modules/darwin/homebrew-server.nix.
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
