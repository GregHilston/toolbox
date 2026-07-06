# Toolbox

## Pixel 8 (Termux)

Shared storage path: `/data/data/com.termux/files/home/storage/shared/Git/`
- Notes repo: `shared/Git/notes/`
- SSH config: port 8022, user `u0_a305`, IP in `~/.ssh/config`

## Repository Layout

```
claude-commands/        # Global slash commands  (~/.claude/commands/)
claude-skills/          # Global agent skills    (~/.claude/skills/)
dot/                    # Dotfiles managed with GNU Stow
nixos/                  # NixOS and nix-darwin host configurations
bin/                    # Helper scripts (all subdirs on $PATH; e.g. fetch-thread.py, bin/anki/ Anki tools)
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
activation when you run `just fr <host>` or `just dr <host>`. It now manages five
targets, all symlinked into this repo (so they're version-controlled and deploy to
every host that imports `programs/tui`):

- `~/.claude/commands`     → `claude-commands/`
- `~/.claude/skills`       → `claude-skills/`
- `~/.claude/CLAUDE.md`    → `dot/claude/.claude/CLAUDE.md`   (global, cross-repo memory)
- `~/.claude/settings.json`→ `dot/claude/.claude/settings.json` (permissions, hooks, plugins)
- `~/.claude/hooks/`       → `dot/claude/.claude/hooks/`      (e.g. the RTK rewrite hook)

The symlinks are **writable** (they point into the repo, not `/nix/store`) so Claude's
own runtime writes to `settings.json` still work — those just show up as git diffs to
commit or discard.

**Clobber guard:** the activation's `link_repo` helper refuses to overwrite a *real*
file. If a host already has, say, a hand-written `~/.claude/settings.json`, activation
prints a `WARNING` and leaves it untouched. To bring it under management: move that file
into `dot/claude/.claude/`, delete the original, then re-run home-manager.

**Non-Nix hosts**: run `just setup-claude` once after cloning. Since everything is a
symlink into the repo, pulling new commits picks up changes without re-running setup.

### Per-repo CLAUDE.md (reduce context re-discovery)

The repo-managed `~/.claude/CLAUDE.md` is **global** — it loads in every session in every
repo, so keep it lean and cross-cutting. Push project-specifics into a `./CLAUDE.md` in
each repo. For repos that don't have one yet (e.g. `~/Git/ccs`, `~/Git/home-lab`), run
`/init` once to generate a tight map of build/test/run commands + directory layout, so
Claude stops re-deriving the structure every session.

## Dotfiles

**Pattern:** dotfiles are portable, plain-syntax, and stow-deployed (the source of
truth). When a config needs nix-only bits, the portable file sources a small
nix-generated `*.local` overlay that no-ops when absent — e.g. `~/.zshrc` +
`~/.zshrc.local`, `~/.tmux.conf` + `~/.tmux.local.conf`. Overlays must use stable
paths (`/run/current-system/sw/...`), never `${pkgs.*}` store paths (GC-safety).
See `dot/README.md` → "Philosophy: portable base, optional nix overlay".

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

**Full documentation**: See `dot/omlx/CLAUDE.md` for per-model settings, model variants, and configuration.

### Troubleshooting

After `brew upgrade`, the old Python process may hold port 8000, causing the new instance
to crash-loop. Fix with:

```bash
kill $(lsof -ti :8000) 2>/dev/null; launchctl kickstart -k "gui/$(id -u)/org.nixos.omlx"
```

### Adding Model Variants

See `dot/omlx/CLAUDE.md` → "Creating Model Variants" for step-by-step instructions on adding
new model profiles (e.g., extended-context variants). Requires changes to:
1. `nixos/modules/darwin/omlx.nix` (symlink creation)
2. `dot/omlx/.omlx/model_settings.json` (variant configuration)
3. `~/.pi/agent/models.json` (pi model registry)

## Claude Code in Docker

Run Claude Code in an isolated Docker container with persistent authentication and session history.

**Setup** (one-time):
```bash
docker volume create claude-code-config
cd ~/Git/toolbox/claude-code
docker build -t my-claude-code:latest .
```

**Usage**:
```bash
# Start or resume session
claude-docker

# Resume a specific session
claude-docker --resume SESSION_ID
```

**Reference**:
- [Claude Code devcontainer documentation](https://code.claude.com/docs/en/devcontainer)
- [Official reference devcontainer](https://github.com/anthropics/claude-code/tree/main/.devcontainer)

The Docker setup uses a named volume (`claude-code-config`) to persist `~/.claude` across container runs, so your authentication and session history persist between runs. See `claude-code/Dockerfile` for implementation details.

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

## Thread Fetchers — Convert HN & Reddit to Markdown/JSON

CLI tools to fetch Hacker News and Reddit threads and convert them to markdown or JSON.

### Scripts

- **`fetch-thread.py`** — Main entry point. Auto-detects HN vs Reddit from URL/ID and delegates to the appropriate converter.
- **`fetch_hn.py`** — Standalone HN converter (fetch from API, format as markdown or JSON).
- **`fetch_reddit.py`** — Standalone Reddit converter (fetch from API, format as markdown or JSON).
- **`_thread_converters.py`** — Shared library (HTML stripping, platform detection).

### Usage

```bash
# Auto-detect from URL
fetch-thread.py "https://news.ycombinator.com/item?id=48072225"
fetch-thread.py "https://reddit.com/r/python/comments/abc123/title"

# Explicit platform
fetch-thread.py 48072225 hn
fetch-thread.py abc123 reddit python

# JSON output
fetch-thread.py 48072225 hn --format json | jq .

# Save to markdown
fetch-thread.py "https://news.ycombinator.com/item?id=48072225" > thread.md
```

Both markdown (default) and JSON output formats supported. Zero external dependencies.

## NixOS / nix-darwin

See `nixos/CLAUDE.md` for host management, deployment commands, and common mistakes.
