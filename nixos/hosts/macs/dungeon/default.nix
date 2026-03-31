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
  launchd.daemons.prevent-sleep = {
    command = "/usr/bin/caffeinate -s";
    serviceConfig = {
      KeepAlive = true;
      RunAtLoad = true;
    };
  };

  # Ensure the home-lab-config directory exists
  # Auto-clone or pull the home-lab repo (requires SSH keys configured for GitHub)
  # NOTE: Uses postActivation (not custom names) because nix-darwin only runs well-known activation script names.
  # NOTE: sudo -H sets HOME to the target user's home dir (otherwise HOME stays as /var/root
  #       and SSH can't find keys in ~/.ssh)
  system.activationScripts.postActivation.text = lib.mkBefore ''
    set -euo pipefail  # Exit on error, undefined vars, and pipeline failures

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
