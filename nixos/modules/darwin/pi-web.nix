{
  config,
  lib,
  vars,
  ...
}: let
  cfg = config.custom.programs.piWeb;
  user = vars.user.name;
  home = "/Users/${user}";
in {
  options.custom.programs.piWeb.enable = lib.mkEnableOption ''
    PI WEB (https://pi-web.dev), a web UI that keeps pi coding-agent sessions
    alive in real workspaces so they can be supervised from a browser. This
    deploys the repo's config.json; the service itself is installed once by
    `just pi-web-setup` (see below for why nix does not own it)
  '';

  config = lib.mkIf cfg.enable {
    # PI WEB is the one long-running service here that nix deliberately does NOT
    # declare a launchd agent for.
    #
    # `pi-web install` writes ~/Library/LaunchAgents/com.pi-web.{web,sessiond}.plist
    # itself, and src/nativeServices/installedServiceDefinitions.ts re-reads them
    # on every `status`, `doctor`, and `restart`, refusing to continue unless the
    # loaded agent reports the plist PI WEB considers canonical. So the Handy/Ice
    # shape — launchd.user.agents.foo — would not just be redundant here, it would
    # break PI WEB's own lifecycle commands.
    #
    # Nor is `npm install -g` + `pi-web install` run from activation. Activation
    # is root, has no user login session for `launchctl bootstrap`, and this repo
    # already draws the line at "don't do network or repo work in activation"
    # (nixos/CLAUDE.md). It is a documented one-time step instead:
    # `just pi-web-setup`, surfaced by `just checklist`.
    #
    # What nix owns is the config file, and only as a symlink — PI WEB's Settings
    # UI writes back to it, so it points into the repo (writable) rather than
    # /nix/store (read-only). See dot/pi-web/CLAUDE.md.
    system.activationScripts.postActivation.text = ''
      (
        set -euo pipefail

        PI_WEB_CONFIG_DIR="${home}/.config/pi-web"
        mkdir -p "$PI_WEB_CONFIG_DIR"
        # postActivation runs as root, so an unowned mkdir leaves a root-owned
        # directory in the user's home that PI WEB cannot write siblings into.
        chown "${user}" "$PI_WEB_CONFIG_DIR"

        ln -sfn "${home}/Git/toolbox/dot/pi-web/.config/pi-web/config.json" \
          "$PI_WEB_CONFIG_DIR/config.json"

        # Nudge rather than fail: a host can legitimately be configured before
        # the one-time install has been run on it.
        if [ ! -x /opt/homebrew/bin/pi-web ]; then
          echo "  PI WEB config deployed, but pi-web is not installed."
          echo "  Run 'just pi-web-setup' from nixos/ to install and start it."
        else
          echo "✓ PI WEB config deployed"
        fi
      ) || echo "WARNING: PI WEB config block failed; continuing."
    '';
  };
}
