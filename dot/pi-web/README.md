# pi-web

PI WEB configuration, stowed to `~/.config/pi-web`.

```bash
cd dot && stow --no-folding -t "$HOME" pi-web
```

See `CLAUDE.md` for why this is stowed rather than nix-generated, why it binds to
a tailnet address, and why `--no-folding` matters.
