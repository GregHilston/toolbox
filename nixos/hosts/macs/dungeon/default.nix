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

  # Auto-clone or pull the home-lab repo (requires SSH keys configured for GitHub)
  system.activationScripts.cloneHomeLab.text = ''
    USER="${vars.user.name}"
    REPO_DIR="/Users/$USER/Git/home-lab"
    sudo -u "$USER" mkdir -p "/Users/$USER/Git"

    # Test SSH access to GitHub before attempting git operations
    if sudo -u "$USER" ssh -o StrictHostKeyChecking=accept-new -T git@github.com 2>&1 | grep -q "successfully authenticated"; then
      if [ ! -d "$REPO_DIR/.git" ]; then
        echo "Cloning home-lab repo..."
        sudo -u "$USER" git clone git@github.com:GregHilston/home-lab.git "$REPO_DIR"
      else
        echo "Pulling latest home-lab changes..."
        sudo -u "$USER" git -C "$REPO_DIR" pull --ff-only
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
