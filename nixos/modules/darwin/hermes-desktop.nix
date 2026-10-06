# Hermes Desktop as a client of dungeon.
# Schema: Desktop's electron/connection-registry.ts.
{
  lib,
  config,
  pkgs,
  vars,
  ...
}: let
  cfg = config.services.hermesDesktop;
  user = lib.escapeShellArg vars.user.name;
  home = "/Users/${vars.user.name}";

  url = "https://hermes.grehg2.xyz";
  id = "dungeon";

  # Inserts once; later UI choices win.
  register = pkgs.writeShellScript "hermes-desktop-register" ''
    set -euo pipefail
    umask 077
    export PATH="${pkgs.jq}/bin:/usr/bin:/bin"
    dir="${home}/Library/Application Support/Hermes"
    reg="$dir/connections.json"

    # No app data yet: the app's first launch owns it.
    [ -d "$dir" ] || exit 0

    if [ ! -e "$reg" ]; then
      # A v1 file is imported only into a missing registry.
      if [ -e "$dir/connection.json" ]; then
        echo "hermes-desktop: open Hermes once to migrate connection.json, then re-run" >&2
        exit 0
      fi
      printf '%s' '{"version":2,"primary":"local","launchMode":"primary","lastUsed":"local","connections":[{"id":"local","kind":"local","label":"This device"}]}' > "$reg"
    fi

    if ! jq --arg url ${url} --arg id ${id} '
      def key: ascii_downcase | sub("/+$"; "");
      (.connections // []) as $c
      | ($c | map(select((.kind == "remote" or .kind == "cloud") and ((.url // "") | key) == ($url | key))) | first) as $hit
      | if $hit then .
        elif ($c | any(.id == $id)) then error("id \($id) belongs to another gateway")
        else .connections = $c + [{id: $id, kind: "remote", label: $id, url: $url, authMode: "oauth"}]
          | .primary = $id
          | .launchMode = "primary"
        end
    ' "$reg" > "$reg.tmp"; then
      rm -f "$reg.tmp"
      echo "hermes-desktop: could not merge $reg; left untouched" >&2
      exit 0
    fi

    # The app's own formatting differs from jq's.
    if [ "$(jq -cS . "$reg.tmp")" = "$(jq -cS . "$reg")" ]; then
      rm -f "$reg.tmp"
    else
      mv -f "$reg.tmp" "$reg"
      echo "✓ Hermes Desktop: dungeon added as the primary gateway"
    fi

    # Launch reads this; follow the registry's primary.
    if [ ! -e "$dir/connection.json" ] && jq -e --arg id ${id} '.primary == $id' "$reg" >/dev/null; then
      jq -n --arg url "${url}" '{mode: "remote", remote: {url: $url, authMode: "oauth"}, profiles: {}}' \
        > "$dir/connection.json"
      echo "✓ Hermes Desktop: launches against dungeon"
    fi

    # A second poller steals dungeon's Telegram updates.
    if [ -e "${home}/Library/LaunchAgents/ai.hermes.gateway.plist" ] ||
       grep -qsE '^(TELEGRAM_BOT_TOKEN|SLACK_(BOT|APP)_TOKEN|EMAIL_PASSWORD)=.' \
         "${home}/.hermes/.env" "${home}"/.hermes/profiles/*/.env; then
      echo "WARNING: a local Hermes gateway or chat token is still on this Mac." >&2
      echo "  See 'Hermes Desktop' in nixos/docs/darwin-post-deploy.md." >&2
    fi
  '';
in {
  options.services.hermesDesktop.enable =
    lib.mkEnableOption "Hermes Desktop, pointed at dungeon's Hermes";

  config = lib.mkIf cfg.enable {
    # Cask, not the best-effort nix flake.
    homebrew.casks = ["hermes-desktop"];

    # Never fatal to `just dr`.
    system.activationScripts.postActivation.text = lib.mkAfter ''
      /usr/bin/sudo --user=${user} -- ${register} || true
    '';
  };
}
