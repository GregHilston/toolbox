# oMLX Configuration (Stow-managed base + nix-generated overlay)

## Directory Structure

```
dot/omlx/                    # Shared oMLX config (deployed to ~/.omlx on every Mac)
├── README.md               # This file
├── .gitignore
├── .stow-local-ignore      # Excludes .omlx/settings.json + runtime state from stow
└── .omlx/
    ├── settings.json.tpl   # Committed template (1Password refs); `just secrets` → settings.json
    ├── settings.json       # Generated base config (gitignored)
    ├── model_settings.json # Per-model overrides (see CLAUDE.md)
    ├── cache/              # Prefix cache storage (gitignored)
    ├── logs/              # (gitignored)
    ├── models/            # Downloaded models (gitignored)
    └── stats.json         # (gitignored)
```

## Deployment

1. **Base config**: `just secrets` (in `nixos/`) renders `settings.json.tpl` →
   `settings.json` via 1Password (`op inject`).
2. **Activation** (`nixos/modules/darwin/omlx.nix`, on `darwin-rebuild`):
   - symlinks the repo's `model_settings.json` into `~/.omlx/`;
   - deep-merges (`jq -s '.[0] * .[1]'`) the base `settings.json` with the
     nix-generated per-host overlay (from `services.omlxDeploy.cacheSize` in
     `hosts/macs/<host>/default.nix`) into `~/.omlx/settings.json`;
   - restarts the launchd agent.

The activation uses a direct `ln`, not stow, so nothing is symlinked into the repo
working tree. `settings.json` is written by the jq merge (not linked) because it
holds host-specific cache sizes and auth keys; models/cache/logs are runtime or
referenced by absolute path. (`.stow-local-ignore` keeps a manual `just stow omlx`
consistent — only `model_settings.json` links into `~/.omlx`.)

There are no longer per-host `omlx-<host>` stow packages — the overlay is a small
nix-generated JSON (`hot_cache_max_size`, the user's `ssd_cache_dir`, and the
`model_dir`, which also corrects the base template's hardcoded username).

## Per-host cache sizing (`hot_cache_max_size`)

Prefix caching keeps KV tensors for recently-seen sequences (e.g. shared system
prompts) in RAM — roughly 1.55× faster time-to-first-token on cache hits. Sizes are
tuned to leave room for model weights + inference on each machine's unified memory:

| Host    | Hardware | RAM   | `cacheSize` | Notes |
|---------|----------|-------|-------------|-------|
| moria   | M4 Max   | 128GB | `32GB`      | Runs the oMLX server + the big models |
| citadel | M5 Pro   | 48GB  | `12GB`      | Work laptop (~25% of RAM) |
| dungeon | M3 Pro   | 36GB  | `8GB`       | Mostly a client of moria; conservative |

To change a host's size, edit `cacheSize` in `hosts/macs/<host>/default.nix` and
`just dr <host>`.

## Key base settings

- **ssd_cache_dir**: null in the base (RAM-only); the overlay sets a per-user
  `~/.omlx/kv-cache` path. SSD spill is left `auto`.
- **max_context_window**: 262144 tokens (`sampling.max_context_window` in the
  template) — caps all models server-wide; see the "Global Context Window Cap"
  gotcha in `CLAUDE.md`.
- **auth**: `api_key`/`secret_key` injected from 1Password via the template.
