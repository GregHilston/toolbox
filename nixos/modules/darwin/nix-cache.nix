# The Macs' shared Nix cache, Attic on dungeon (home-lab docs/nix-cache.md).
# Every Mac downloads from it; the host that sets `push` uploads.
{
  config,
  lib,
  pkgs,
  ...
}: let
  cfg = config.custom.nixCache;
in {
  options.custom.nixCache.push = lib.mkEnableOption "the attic CLI, so `just diff` uploads its builds";

  config = {
    # Determinate reads this; nix.settings is off here.
    environment.etc."nix/nix.custom.conf" = {
      text = ''
        extra-substituters = https://cache.grehg2.xyz/darwin
        extra-trusted-public-keys = darwin:6KuIpoQ8Hbry5cIzWPQBHQpAXcVefqmVgxHJDdaoP30=
        # Nix retries 5 times; keep each short.
        connect-timeout = 1
      '';
      # The installer's comment-only file, replaced once.
      knownSha256Hashes = ["3bd68ef979a42070a44f8d82c205cfd8e8cca425d91253ec2c10a88179bb34aa"];
    };

    # The daemon reads config only at start.
    system.activationScripts.postActivation.text = lib.mkAfter ''
      (
        conf=$(readlink -f /etc/nix/nix.custom.conf)
        marker=/var/db/nix-custom-conf.applied
        if [ "$(cat "$marker" 2>/dev/null)" != "$conf" ]; then
          launchctl kickstart -k system/systems.determinate.nix-daemon && echo "$conf" > "$marker"
        fi
      ) || echo "WARNING: could not restart the Nix daemon; restart it for the cache."
    '';

    # `just diff` uploads with it; watch-store crashes (attic#226).
    environment.systemPackages = lib.mkIf cfg.push [pkgs.attic-client];
  };
}
