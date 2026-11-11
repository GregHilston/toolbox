# Toolbox

---

My toolbox contains a series of configuration files, helper scripts, and automations to allow me to quickly configure an OSX or Linux environment.

## What's In This Repo?

Run `ls`: each top-level directory has one job. Start with `nixos/` for hosts, `dot/` for dotfiles, `bin/` for scripts on `$PATH`, and `skills/` for agent skills. `CLAUDE.md` is the repo guide, and `just --list` shows the root recipes.

## Household Finances

moria and dungeon get the tools for a plain-text household ledger (Beancount and
Fava) through `nixos/modules/darwin/finance.nix`. How the ledger works, and every
command to run it, is in the private home-lab repo:
[`finance/README.md`](https://github.com/GregHilston/home-lab/blob/main/finance/README.md).
No financial data or categories live here.

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

**Pinning / bumping difit:** the pinned version lives in one place — `DIFIT_VERSION` at the top of `bin/difit.sh`. Bump it by editing that default, or override per-run with `DIFIT_VERSION=<version> difit …`. Pinning avoids `npx`'s stale-cache footgun and keeps runs reproducible.

## Fonts

Fonts are provisioned declaratively by Stylix on the nix-managed hosts — see
`nixos/modules/stylix/`. Nothing to install by hand.
