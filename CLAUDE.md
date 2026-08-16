# Toolbox

<!-- The Pixel 8 (Termux) paths used to be duplicated here from the global
     ~/.claude/CLAUDE.md (dot/claude/.claude/CLAUDE.md) — same paths and port,
     differing only in one label. Both files load in every session in this
     repo, so the copy was duplicated context. The global one is
     authoritative. -->

## Repository Layout

```
claude-commands/        # Global slash commands  (~/.claude/commands/)
claude-skills/          # Global agent skills    (~/.claude/skills/)
claude-code/            # Dockerfile + docs for Claude Code in a container
dot/                    # Dotfiles managed with GNU Stow
nixos/                  # NixOS and nix-darwin host configurations
bin/                    # Helper scripts (all subdirs on $PATH) — see bin/CLAUDE.md
windows/                # Windows provisioning (autounattend.xml, scoop/winget lists)
```

## Claude Commands and Skills

### Adding a new slash command

Create a markdown file in `claude-commands/`:

```
claude-commands/my-command.md
```

It becomes available as `/my-command` in any Claude Code session.

> **Note:** the whole `claude-commands/` directory is symlinked into
> `~/.claude/commands/`, so **every** `.md` file there becomes a slash command
> (a `README.md` would register as `/README`). Keep docs elsewhere.

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

## Voice Input — Hold Caps Lock to Dictate

Caps Lock stops toggling caps: a quick tap sends `Escape`, holding it sends `F18` for the
duration. [Handy](https://handy.computer/) binds that `F18` as its push-to-talk key and
transcribes locally (Whisper / Parakeet — audio never leaves the machine).

Two implementations, one hotkey. macOS: Karabiner-Elements — see `dot/karabiner/`.
NixOS GUI hosts: `services.keyd` — see `nixos/modules/common/keyd.nix`.

Handy has to be *running* for the hotkey to do anything, so it's started declaratively
rather than by hand: a launchd agent on macOS (`nixos/modules/darwin/handy.nix`, imported
by citadel and moria — headless dungeon skips it) and a home-manager systemd user service
bound to `graphical-session.target` on NixOS GUI hosts (`nixos/modules/home/default.nix`).
Handy's own "Launch at login" toggle stays off; it writes app state nix doesn't own. Ice
(below) is started the same way — the shared rationale for the launchd `open -a` shape lives
in `nixos/CLAUDE.md` → "Launching GUI apps at login".

On macOS this only takes effect once Karabiner's driver extension is approved on that
host — until then Caps Lock still toggles caps. That grant, Handy's mic/accessibility
grants, and Handy's own hotkey setting are GUI-gated and can't be declared; they're in
`nixos/docs/darwin-post-deploy.md` (`just checklist`).

## Menu Bar — Ice

[Ice](https://github.com/jordanbaird/Ice) manages the macOS menu bar (hides the overflow
icons the notch would otherwise swallow). Cask `jordanbaird-ice` in
`nixos/modules/darwin/homebrew-base.nix`; launched at login by
`nixos/modules/darwin/ice.nix`, imported from `modules/darwin/common.nix` so all three Macs
get it. Same pattern as Handy above (`nixos/CLAUDE.md` → "Launching GUI apps at login"): a
launchd `open -a` agent, `RunAtLoad` only, and Ice's own "Launch at login" toggle stays
**off** so the two don't double-register. Ice's Accessibility + Screen Recording grants are
GUI-gated — `nixos/docs/darwin-post-deploy.md`.

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

Local LLM inference server (Apple Silicon). Config in `dot/omlx/`. Managed as a launchd
service (`org.nixos.omlx`) on port 8000.

Per-host differences are generated by nix, not stowed: `nixos/modules/darwin/omlx.nix`
merges the base `settings.json` with a per-host overlay. It replaced the old
`dot/omlx-<host>/` stow packages, which no longer exist.

Note the merge base `dot/omlx/.omlx/settings.json` is **generated, not committed** — it
holds secrets, so only `settings.json.tpl` is in git. Run `just secrets` in `nixos/` before
the first activation on a new host, or the merge has nothing to read.

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

Run Claude Code in an isolated Docker container that shares your host auth and session history.

**Usage** (the `claude-docker` function in `dot/zsh/.zshrc` builds the image on first run):
```bash
# Start or resume session
claude-docker

# Resume a specific session
claude-docker --resume SESSION_ID
```

The container **bind-mounts** your real `~/.claude` and mounts `~/Git` at its
actual host path, so credentials, sessions, and project identities are shared
directly between host and container (no named volume). See
`claude-code/CLAUDE.md` for the full flag-by-flag explanation and the
[devcontainer reference](https://github.com/anthropics/claude-code/tree/main/.devcontainer).

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
2. **Headless hosts (dungeon)**: the desktop-app integration is GUI-gated, so `op inject`
   there fails with `authorization timeout`. Preferred fix is a **1Password service
   account token** (needs a Business/Teams plan) at `~/.config/op/service-account-token`,
   mode `600` — `just secrets` picks it up automatically and needs no GUI. Without a
   token, connect via VNC (Finder → Go → Connect to Server) and unlock 1Password first.

## Thread Fetchers — Convert HN & Reddit to Markdown/JSON

`fetch-thread.py` prints a Hacker News or Reddit thread as markdown, or `--format json`.
Zero external dependencies.

Give it a **URL** and the platform is auto-detected. A **bare ID** can't be — pass the
platform as the next argument (and the subreddit, for Reddit):

```bash
fetch-thread.py https://news.ycombinator.com/item?id=48072225
fetch-thread.py 48072225 hn
fetch-thread.py abc123 reddit python
```

`fetch-thread.py -h` has the full reference. (With no arguments it only prints the
two-line argparse usage stanza to stderr, not the examples.)

## Local Diff & PR Viewers — diff2html & difit

Browser-based git diff viewers, both Mac-only (they need a node runtime):

- `dhtml` / `dhtmls` / `dhtmlside` — diff2html, quick working-tree views.
- `difit` — a GitHub-PR-like UI. Version-pinned; `DIFIT_VERSION` in `bin/difit.sh` is the
  single source of truth, so bump it there.
- `gpr` — the current branch as a PR diff against an auto-detected base.

Note our `difit.sh` defaults a missing target to `.` (all uncommitted changes); upstream
difit would show the last commit instead.

See the root `README.md` for the full flag reference, and `bin/difit.sh` / `bin/git-pr.sh`
for the wrappers themselves.

## NixOS / nix-darwin

See `nixos/CLAUDE.md` for host management, deployment commands, and common mistakes.
