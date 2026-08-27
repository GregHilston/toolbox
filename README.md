# Toolbox

---

My toolbox contains a series of configuration files, helper scripts, and automations to allow me to quickly configure an OSX or Linux environment.

## What's In This Repo?

```bash
├── bin/                                    # Helper scripts. Added to $PATH (recursive) for user convenience.
├── claude-code/                            # Dockerfile + docs for running Claude Code in a container.
├── claude-commands/                        # Global Claude Code slash commands (→ ~/.claude/commands/).
├── claude-skills/                          # Global Claude Code agent skills (→ ~/.claude/skills/).
├── dot/                                    # Dotfiles to configure a slew of programs and environments.
├── nixos/                                  # NixOS and nix-darwin configurations for all hosts.
├── tests/                                  # Tests for bin/ scripts (`just test`). Not under bin/, which is on $PATH.
├── windows/                                # Windows provisioning (autounattend.xml, scoop/winget lists).
├── justfile                                # Root recipes (`just setup-claude`, `just test`).
├── CLAUDE.md                               # Repo guide for Claude Code (and humans).
├── README.md                               # This documentation.
```

## How Do I Use This Repo?

See the [nixos/](nixos/) directory for NixOS and nix-darwin host configurations. Each host is managed declaratively via Nix flakes.

## Local Diff & PR Viewers

Two browser-based diff viewers for reviewing changes locally, without pushing anything or opening a GitHub PR. Both are **Mac-only** — they need a Node.js runtime (`npx`), which the Macs have (citadel via volta; dungeon/moria via Homebrew) but the NixOS hosts do not (node lives only inside per-project dev shells there).

### View your working-tree changes — `diff2html`

Installed via nixpkgs (`diff2html-cli`). Opens the diff in your browser.

```bash
dhtml        # all changes vs HEAD (staged + unstaged), unified
dhtmls       # staged changes only
dhtmlside    # all changes vs HEAD, side-by-side
```

Or drive it directly: `git diff --no-ext-diff HEAD | diff2html -i stdin`
(`--no-ext-diff` is required because git is configured to use difftastic as its external diff).

### Review a branch as a PR — `difit` / `gpr`

`difit` renders a GitHub-PR-like UI in the browser. It is not in nixpkgs, so it runs via `npx` pinned to an exact version.

```bash
# Working-tree changes (alternative to diff2html)
difit                  # all uncommitted changes (staged + unstaged) — the default
difit staged           # staged only
difit working          # unstaged only

# This branch vs a base, PR-style
gpr                          # vs the repo's default branch (auto-detected, e.g. origin/main)
gpr origin/develop           # vs an explicit base
difit HEAD main --merge-base # equivalent, done by hand

# Don't open a browser / pick a port
gpr --no-open --port 5000
```

`gpr` auto-detects the base branch from `origin/HEAD` (falling back to `main`/`master`) and uses GitHub's 3-dot (`--merge-base`) semantics by default; set `GPR_MERGE_BASE=0` for a plain 2-dot diff.

**Pinning / bumping difit:** the pinned version lives in one place — `DIFIT_VERSION` at the top of `bin/difit.sh` (currently `5.0.6`). Bump it by editing that default, or override per-run with `DIFIT_VERSION=5.1.0 difit …`. Pinning avoids `npx`'s stale-cache footgun and keeps runs reproducible.

## Fonts

Fonts are provisioned declaratively by Stylix on the nix-managed hosts — see
`nixos/modules/stylix/`. Nothing to install by hand.
