# PI WEB

Config for [PI WEB](https://pi-web.dev/) — a web UI that keeps pi coding-agent
sessions alive in real workspaces, so they can be supervised from a phone or
tablet instead of a terminal. Stowed to `~/.config/pi-web`.

Only **moria** runs it (`custom.programs.piWeb.enable` in
`nixos/modules/darwin/pi-web.nix`). It is the M4 Max with 128 GB and already
runs the local oMLX server, so sessions and inference stay on one box.

## Why this is stowed and not `home.file`

PI WEB's **Settings** UI writes back to `config.json`. A `home.file` entry is a
read-only `/nix/store` symlink, so every save in the browser would fail. Stow
gives a symlink that points into *this repo* — writable, still
version-controlled, and UI edits show up as ordinary git diffs to commit or
discard. Same reasoning as `~/.claude/settings.json`; see the root `CLAUDE.md`.

Stow it with `--no-folding`. `~/.config/pi-web` does not otherwise exist, so a
plain `stow` folds the whole directory into one symlink at the repo and PI WEB
then writes runtime state inside the working tree — the hazard `dot/justfile`
already documents for `pi` and `omlx`.

## Why it binds to a tailnet address

**PI WEB ships no authentication.** Anything that can reach the port gets a
shell, a file browser, and an agent on this machine. Binding `0.0.0.0` would
hand that to every device on the home LAN, so it binds to moria's tailnet
address instead: home-lab's Caddy on dungeon reverse-proxies `pi.grehg2.xyz`
over the tailnet, and nothing off the tailnet can reach it at all.

That address is duplicated here and in `nixos/config/vars.nix`
(`networking.hosts.moria.tailscale`). Accepted wart — a stowed JSON file cannot
read nix vars. vars.nix is the canonical copy; if the tailnet address ever
changes, both need updating.

## Runtime state is not here

PI WEB keeps its project/machine registries, session archives, and daemon socket
under `~/.pi-web` (`PI_WEB_DATA_DIR`), which is deliberately outside this repo.
Per-project settings live in `<project>/.pi-web/config.json`.

Full key reference: <https://pi-web.dev/config>.
