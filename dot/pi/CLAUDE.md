# Pi (pi-mono)

Dotfiles for the pi coding agent, stowed to `~/.pi`.

## Secret Management

`models.json` contains the oMLX API key and is generated from `models.json.tpl` via `just secrets` (1Password `op inject`). `settings.json` is managed by home-manager (pi.nix) and contains no secrets.

## Gotcha: Context Window Errors

Pi's `models.json` declares per-model context windows, but oMLX enforces a **global** `sampling.max_context_window` in its own settings (`dot/omlx/.omlx/settings.json`). If pi reports "exceeds max context window" with a suspiciously low limit, check the oMLX server config — not just pi's model definitions.
