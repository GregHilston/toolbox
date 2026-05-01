# Toolbox

## Repository Layout

```
claude-commands/        # Global slash commands  (~/.claude/commands/)
claude-skills/          # Global agent skills    (~/.claude/skills/)
dot/                    # Dotfiles managed with GNU Stow
nixos/                  # NixOS and nix-darwin host configurations
bin/                    # Helper scripts
```

## Claude Commands and Skills

### Adding a new slash command

Create a markdown file in `claude-commands/`:

```
claude-commands/my-command.md
```

It becomes available as `/my-command` in any Claude Code session.

### Adding a new skill

Create a subdirectory with a `SKILL.md` file in `claude-skills/`:

```
claude-skills/my-skill/SKILL.md
```

The `SKILL.md` must include YAML frontmatter:

```markdown
---
name: my-skill
description: |
  What this skill does and when Claude should use it.
model: inherit
tools: ["Bash"]
---

Agent instructions here...
```

It becomes available as `/my-skill` in any Claude Code session.

### How they reach each host

**Nix-managed hosts** (NixOS / nix-darwin): automatic. The home-manager module at
`nixos/modules/programs/tui/claude.nix` creates the symlinks during `home-manager`
activation when you run `just fr <host>` or `just dr <host>`.

**Non-Nix hosts**: run once after cloning this repo:

```bash
just setup-claude
```

This creates:
- `~/.claude/commands` → `~/Git/toolbox/claude-commands`
- `~/.claude/skills`   → `~/Git/toolbox/claude-skills`

Since these are symlinks into the repo, pulling new commits automatically makes new
commands and skills available without re-running any setup.

## Dotfiles

See `dot/` — managed with GNU Stow. Run from the `dot/` directory:

```bash
just stow <package>     # symlink a single package
just stow-all           # symlink all packages
```

### Stow gotchas

- **Always pass `-t $HOME`** (or use `just stow`). Bare `stow <pkg>` from `~/Git/toolbox/dot/`
  targets the parent directory (`~/Git/toolbox/`), not `$HOME`. This silently creates junk
  symlinks inside the repo instead of in your home directory.
- In nix activation scripts, use `stow -d "$HOME/Git/toolbox/dot" -t "$HOME" <pkg>` since
  the working directory may not be the dot dir.
- `lib.hm.dag.entryAfter` is available in NixOS home-manager modules (`modules/home/default.nix`)
  but **not** in nix-darwin's `home-manager.users.<name>` block (`modules/darwin/home.nix`).
  For Darwin, use declarative options like `xdg.configFile` instead of activation scripts.

## Plex

### .plexmatch files

Place a `.plexmatch` file in a show's root folder to pin it to a specific database ID. This prevents Plex from merging shows that share a name (e.g. a reboot and the original series).

```
tvdbid: 465690
```

Use `tvdbid` or `tmdbid`. Rescan the library after adding the file.

## Searxngr — Privacy-Focused Search

CLI for dungeon's self-hosted SearXNG instance. Config managed via stow (`dot/searxngr-config/`), binary installed via `uv tool install`. See `/searxngr-search` skill for Claude Code integration.

## oMLX

Local LLM inference server (Apple Silicon). Config in `dot/omlx/`, per-host overrides in
`dot/omlx-{hostname}/`. Managed as a launchd service (`org.nixos.omlx`) on port 8000.

After `brew upgrade`, the old Python process may hold port 8000, causing the new instance
to crash-loop. Fix with:

```bash
kill $(lsof -ti :8000) 2>/dev/null; launchctl kickstart -k "gui/$(id -u)/org.nixos.omlx"
```

## Secret Management

All secrets live in 1Password (vault: **Infra**). Committed `.tpl` template files contain
`{{ op://Infra/Item/field }}` references. Run `just secrets` from `nixos/` to generate
the real files via `op inject`. Generated files are gitignored.

```bash
cd nixos && just secrets    # generates dot/omlx settings.json, dot/pi models.json, secrets/.env
```

Never commit plaintext secrets. If a new secret is needed, add it to 1Password and reference
it in the appropriate `.tpl` file.

### Prerequisites

1. **1Password CLI integration**: Open 1Password app → Settings → Developer → enable
   "Integrate with 1Password CLI". This must be done manually on each machine.
2. **Headless hosts (dungeon)**: `just secrets` requires 1Password GUI authentication
   (Touch ID / password prompt). On headless Macs, connect via VNC first
   (Finder → Go → Connect to Server) before running `just secrets`.

## NixOS / nix-darwin

See `nixos/CLAUDE.md` for host management, deployment commands, and common mistakes.
