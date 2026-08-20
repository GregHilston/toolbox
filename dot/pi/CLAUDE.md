# Pi (pi-mono)

Dotfiles for the pi coding agent, stowed to `~/.pi`.

## Secret Management

`models.json` contains the oMLX API key and is generated from `models.json.tpl` via `just secrets` (1Password `op inject`). `settings.json` is managed by home-manager (pi.nix) and contains no secrets.

`secrets.json` holds API keys for third-party extensions (currently
`BRAVE_API_KEY` for pi-brave-search) and is likewise generated from
`secrets.json.tpl` via `just secrets`.

**Why a file and not a shell export.** Extensions read their keys from
`process.env`, but PI WEB's session daemon is a launchd agent — it never sources
`~/.zshrc`, and its plist environment is a modeled set that `pi-web doctor`
validates, so neither route reaches a browser session. The `pi-secrets`
extension reads the file into `process.env` from inside pi instead, which
behaves identically in the TUI and in PI WEB. A real environment variable still
wins, so `BRAVE_API_KEY=... pi` works for a one-off.

The Reddit session cookie is deliberately *not* in here. `reddit-research.json`
is declared by pi.nix and points at `~/.config/pi-reddit-research/cookie.txt`, a
hand-edited file — Reddit expires the cookie every few days, and re-running
`just secrets` on every host that often is worse than editing one file.

## Gotcha: Context Window Errors

Pi's `models.json` declares per-model context windows, but oMLX enforces a **global** `sampling.max_context_window` in its own settings (`dot/omlx/.omlx/settings.json`). If pi reports "exceeds max context window" with a suspiciously low limit, check the oMLX server config — not just pi's model definitions.
