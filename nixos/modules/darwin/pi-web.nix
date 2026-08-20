{
  config,
  lib,
  vars,
  ...
}: let
  cfg = config.custom.programs.piWeb;
  user = vars.user.name;
  home = "/Users/${user}";
  host = config.networking.hostName;

  # The stowed config is plain JSON, so it cannot read vars.nix — the bind
  # address is necessarily written out in both places. Read it back here and
  # assert they agree, so the duplication is checked at eval time instead of
  # drifting silently until PI WEB is unreachable through Caddy.
  repoConfig = builtins.fromJSON (builtins.readFile ../../../dot/pi-web/.config/pi-web/config.json);
in {
  options.custom.programs.piWeb.enable = lib.mkEnableOption ''
    PI WEB (https://pi-web.dev), a web UI that keeps pi coding-agent sessions
    alive in real workspaces so they can be supervised from a browser. This
    deploys the repo's config.json; the service itself is installed once by
    `just pi-web-setup` (see below for why nix does not own it)
  '';

  config = lib.mkIf cfg.enable {
    assertions = [
      {
        assertion = repoConfig.host == vars.networking.hosts.moria.tailscale;
        message = ''
          dot/pi-web/.config/pi-web/config.json binds to "${repoConfig.host}", but
          vars.networking.hosts.moria.tailscale is "${vars.networking.hosts.moria.tailscale}".
          home-lab's Caddy proxies pi.grehg2.xyz to the vars address, so these must
          agree or PI WEB is unreachable through it. vars.nix is canonical.
        '';
      }
    ];

    # PI WEB is the one long-running service here that nix deliberately does NOT
    # declare a launchd agent for.
    #
    # `pi-web install` generates ~/Library/LaunchAgents/com.pi-web.{web,sessiond}.plist
    # from its own plan (dist/nativeServices/serviceRendering.js) and *replaces*
    # them on every run. `pi-web doctor` then re-reads what is installed and
    # compares it to that plan — shellCommand and workingDirectory must match, and
    # the two agents must agree with each other (dist/nativeServices/serviceDoctor.js).
    # So a nix-declared launchd.user.agents block is not merely redundant: it
    # either loses to the next `pi-web install` or fails doctor, and doctor is the
    # tool you reach for when PI WEB misbehaves.
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
        # postActivation runs as root, so a bare `mkdir -p` leaves every level it
        # has to create owned by root — including ~/.config on a fresh host.
        # `install -d` sets the owner as it goes.
        install -d -o "${user}" -g staff "${home}/.config" "$PI_WEB_CONFIG_DIR"

        PI_WEB_CONFIG="$PI_WEB_CONFIG_DIR/config.json"
        PI_WEB_REPO_CONFIG="${home}/Git/toolbox/dot/pi-web/.config/pi-web/config.json"

        # Same clobber guard as link_repo in modules/programs/tui/claude.nix.
        # It matters here specifically: if `just pi-web-setup` runs before this
        # module is deployed, `pi-web install` writes a REAL default config
        # (127.0.0.1:8504) at this path, and a bare `ln -sfn` would silently
        # delete it — reverting the bind address with no message.
        if [ -L "$PI_WEB_CONFIG" ]; then
          ln -sfn "$PI_WEB_REPO_CONFIG" "$PI_WEB_CONFIG"
        elif [ ! -e "$PI_WEB_CONFIG" ]; then
          ln -s "$PI_WEB_REPO_CONFIG" "$PI_WEB_CONFIG"
        else
          echo "WARNING: $PI_WEB_CONFIG is a real file, not a symlink — leaving it untouched." >&2
          echo "  PI WEB is running on its own config, not the repo's. To adopt it:" >&2
          echo "    mv '$PI_WEB_CONFIG' '$PI_WEB_REPO_CONFIG' && just dr ${host}" >&2
        fi
        chown -h "${user}" "$PI_WEB_CONFIG" 2>/dev/null || true

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
