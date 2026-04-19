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

## Plex

### .plexmatch files

Place a `.plexmatch` file in a show's root folder to pin it to a specific database ID. This prevents Plex from merging shows that share a name (e.g. a reboot and the original series).

```
tvdbid: 465690
```

Use `tvdbid` or `tmdbid`. Rescan the library after adding the file.

## NixOS / nix-darwin

See `nixos/CLAUDE.md` for host management, deployment commands, and common mistakes.
