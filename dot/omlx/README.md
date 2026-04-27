# oMLX Configuration (Stow-managed)

## Directory Structure

This directory uses **GNU Stow** to manage oMLX dotfiles with per-machine overrides:

```
dot/
├── omlx/                    # Base oMLX config (shared across all machines)
│   ├── README.md           # This file
│   ├── .gitignore
│   └── .omlx/
│       ├── settings.json   # Base template (SSD caching disabled)
│       ├── cache/          # Prefix cache storage (hot_cache_max_size controlled)
│       ├── logs/
│       ├── models/         # Downloaded models (gitignored)
│       └── stats.json
│
├── omlx-moria/             # Moria-specific overrides (stow applies after base)
│   └── .omlx/
│       └── settings.json   # Override: hot_cache_max_size=32GB (M4 Max 128GB)
│       └── README.md       # Why these settings
│
└── omlx-dungeon/           # Dungeon-specific overrides (stow applies after base)
    └── .omlx/
        └── settings.json   # Override: hot_cache_max_size=8GB (M3 Pro 36GB)
        └── README.md       # Why these settings
```

## Deployment Strategy

**GNU Stow** allows multiple packages to coexist. Later stow operations override earlier ones.

### On Moria
```bash
cd ~/Git/toolbox/dot
stow omlx omlx-moria
```
- Links base config from `omlx/`
- Overrides `settings.json` with `omlx-moria/` version
- Result: Base config + moria-specific hot cache settings

### On Dungeon
```bash
cd ~/Git/toolbox/dot
stow omlx omlx-dungeon
```
- Links base config from `omlx/`
- Overrides `settings.json` with `omlx-dungeon/` version
- Result: Base config + dungeon-specific hot cache settings

## NixOS Automation

Each machine's NixOS config automatically runs stow during activation:

```nix
# In hosts/macs/moria/default.nix or dungeon/default.nix
system.activationScripts.postActivation.text = lib.mkBefore ''
  cd ~/Git/toolbox/dot
  stow omlx omlx-<hostname>
'';
```

This ensures the correct oMLX config is deployed every time you run `darwin-rebuild switch`.

## Why This Approach?

1. **DRY (Don't Repeat Yourself)**: Shared config lives in `omlx/`, differences isolated in `omlx-moria/` and `omlx-dungeon/`
2. **Git-friendly**: Base config and overrides tracked separately, clear diffs
3. **Reproducible**: Every machine gets the right settings automatically via NixOS
4. **Maintainable**: If you add a new setting to base, all machines inherit it automatically

## Key Settings

See `omlx-moria/README.md` and `omlx-dungeon/README.md` for detailed explanations of why each machine has its settings.

**TL;DR:**
- **hot_cache_max_size**: Prefix caching (system prompts, code context) reused across requests. Larger = faster repeated prompts.
- **ssd_cache_dir**: Disabled (set to null) — rely on RAM only for simplicity
- **max_context_window**: 32K tokens, suitable for code/document workflows
