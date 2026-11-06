# The Macs' shared Nix cache, Attic on dungeon (home-lab docs/nix-cache.md).
# Every Mac downloads from it; the host that sets `push` uploads what it builds.
{
  config,
  lib,
  pkgs,
  vars,
  ...
}: let
  cfg = config.custom.nixCache;
in {
  options.custom.nixCache.push = lib.mkEnableOption "uploading every new store path to the cache";

  config = {
    # Determinate reads this; nix.settings is off here.
    environment.etc."nix/nix.custom.conf" = {
      text = ''
        extra-substituters = https://cache.grehg2.xyz/darwin
        extra-trusted-public-keys = darwin:6KuIpoQ8Hbry5cIzWPQBHQpAXcVefqmVgxHJDdaoP30=
        # Off the tailnet, fall through fast.
        connect-timeout = 5
      '';
      # The installer's comment-only file, replaced once.
      knownSha256Hashes = ["3bd68ef979a42070a44f8d82c205cfd8e8cca425d91253ec2c10a88179bb34aa"];
    };

    # The daemon reads its config only at start.
    system.activationScripts.postActivation.text = lib.mkAfter ''
      (
        conf=$(readlink -f /etc/nix/nix.custom.conf)
        marker=/var/db/nix-custom-conf.applied
        if [ "$(cat "$marker" 2>/dev/null)" != "$conf" ]; then
          launchctl kickstart -k system/systems.determinate.nix-daemon
          echo "$conf" > "$marker"
        fi
      ) || echo "WARNING: could not restart the Nix daemon; restart it for the cache."
    '';

    # Pushes only paths cache.nixos.org lacks.
    launchd.user.agents.attic-watch-store = lib.mkIf cfg.push {
      serviceConfig = {
        ProgramArguments = ["${pkgs.attic-client}/bin/attic" "watch-store" "lab:darwin"];
        RunAtLoad = true;
        KeepAlive = true;
        # Quiet retries while dungeon is unreachable.
        ThrottleInterval = 60;
        EnvironmentVariables.PATH = "/nix/var/nix/profiles/default/bin:/usr/bin:/bin";
        StandardOutPath = "/Users/${vars.user.name}/Library/Logs/attic-watch-store.log";
        StandardErrorPath = "/Users/${vars.user.name}/Library/Logs/attic-watch-store.log";
      };
    };
  };
}
