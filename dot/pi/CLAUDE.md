# Pi (pi-mono)

Dotfiles for the pi coding agent, stowed to `~/.pi`.

## Secret Management

`models.json` contains the oMLX API key and is generated from `models.json.tpl` via `just secrets` (1Password `op inject`). `settings.json` is managed by home-manager (pi.nix) and contains no secrets.

`secrets.json` holds API keys for third-party extensions (currently
`BRAVE_API_KEY` for pi-brave-search) and is likewise generated from
`secrets.json.tpl` via `just secrets`.

**Why a file and not a shell export.** Extensions read their keys from
`process.env`, and the obvious home for one is `~/.zshrc.local`. That does not
reach a PI WEB session: its launchd agents run `/usr/bin/env zsh -lc <cmd>`, a
*login* but **non-interactive** shell, so `~/.zshenv` and `~/.zprofile` are
sourced and `~/.zshrc` is skipped — and `~/.zshrc.local` is sourced by
`~/.zshrc`. `~/.zshenv` would work, but it exports the key to every process on
the machine and this repo does not manage that file. Putting it in PI WEB's
launchd plists does not stick either, since `pi-web install` regenerates them.

Reading the file from inside pi is scoped to pi, survives PI WEB upgrades, and
behaves identically in the TUI and the browser. A real environment variable
still wins, so `BRAVE_API_KEY=... pi` works for a one-off.

The Reddit session cookie is deliberately *not* in here. `reddit-research.json`
is declared by pi.nix and points at `~/.config/pi-reddit-research/cookie.txt`, a
hand-edited file — Reddit expires the cookie every few days, and re-running
`just secrets` on every host that often is worse than editing one file.

## Gotcha: Context Window Errors

Pi's `models.json` declares per-model context windows, but oMLX enforces a **global** `sampling.max_context_window` in its own settings (`dot/omlx/.omlx/settings.json`). If pi reports "exceeds max context window" with a suspiciously low limit, check the oMLX server config — not just pi's model definitions.
