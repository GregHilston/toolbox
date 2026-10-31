# Toolbox

## Repository Layout

`ls` answers this. `bin/**` is recursively on `$PATH`, so helpers work from any repo.

## Claude Commands and Skills

### Adding a new slash command

Drop a `.md` in `claude-commands/`; it becomes `/<name>` everywhere.

> **Trap:** the whole directory is symlinked into `~/.claude/commands/`, so **every**
> `.md` there becomes a command — a `README.md` would register as `/README`. Keep docs
> elsewhere.

### Adding a new skill

**Follow `skills/README.md`.** One skill set reaches Claude Code, pi and
Hermes, and a tool is a script in `bin/` plus a thin skill that names it.
`tests/test_skills.py` enforces the rules.

### Matt Pocock's skills

`skills/wayfinder/` is the entry point (`/wayfinder` here, `/skill:wayfinder`
in pi) for planning work too big for one session: a map of decision tickets on the
repo's issue tracker, resolved one per session. Run `setup-matt-pocock-skills` once
per target repo; it writes the tracker doc the others read.

Any skill whose `metadata.upstream` points at
[mattpocock/skills](https://github.com/mattpocock/skills) (MIT) is copied verbatim
from the commit in `metadata.vendored`, minus the Codex-only `agents/openai.yaml`.
The only local edit is a trailing **Tool mapping** table where a skill names a
tool, so pi (no Skill tool, no `AskUserQuestion`, subagents only under
`pi-subagents`) runs the same file. To update, copy the new upstream over, keep
each table, and bump the commit in both metadata fields.

They read a repo's glossary from `GLOSSARY.md` (formerly `CONTEXT.md`).

### How they reach each host

Nix hosts get `commands`, `skills`, the global `CLAUDE.md`, `settings.json`, `hooks` and the
ccstatusline config as symlinks into this repo, from `nixos/modules/programs/tui/claude.nix`
on `just fr/dr <host>`. Non-Nix hosts run `just setup-claude` once. Full list and the
RTK hook: `nixos/CLAUDE.md` → "Claude Code on each host".

- **Clobber guard:** `link_repo` refuses to overwrite a *real* file and only warns. Move the
  file into `dot/claude/.claude/`, delete the original, re-run home-manager.
- The global gitignore ignores `.claude/`, so a new file under `dot/claude/.claude/` needs
  `git add -f`. Check `git show --stat`.
- `settings.json` sets `CLAUDE_CODE_FORCE_SESSION_PERSISTENCE=1`: Claude Code's
  `CLAUDE_CODE_CHILD_SESSION=1` marker leaks into relaunched terminals and silently drops
  transcripts. Cost: `claude -p` runs spawned by an agent save one too.

### Status Line — ccstatusline

Layout in `dot/ccstatusline/`, wired by `statusLine` in `settings.json`; widget choices and
their reasons are in `dot/ccstatusline/README.md`. The version pin is `ccstatuslineVersion`
in `nixos/modules/programs/tui/claude.nix`.

## Voice Input — Hold Caps Lock to Dictate

Caps Lock sends F18 (Shift: F19 Command Mode, Option: F20 Write Mode); FluidVoice on moria
and citadel, Handy on NixOS. Keys, launching, model routing and `touch ~/.hide-fv-motd`:
`nixos/CLAUDE.md` → "FluidVoice" and "Launching GUI apps at login".

## Menu Bar — no manager

macOS 27 folds overflow icons behind a » button on its own, and it broke Ice, which
had been unmaintained since 2025: its menu went dead, so quitting took a `kill`. Before
adding a replacement, check it names macOS 27 support. Hidden Bar (`hiddenbar`) does;
Thaw, Ice's successor, only has it in an alpha.

## Mac Utilities — Vorssaint

Menu bar suite on every Mac; `nixos/modules/darwin/vorssaint.nix` owns it and explains
itself, with the overlaps in `nixos/CLAUDE.md` → "Launching GUI apps at login". It has no
config file, so the module seeds `defaults` **once**, gated on the app's own `hasOnboarded`
marker. Editing the feature list does nothing to a Mac already set up until you quit
Vorssaint, `defaults delete com.vorssaint.utils hasOnboarded` and `just dr <host>`.
Permissions stay manual: `nixos/docs/darwin-post-deploy.md`.

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

- **Always pass `-t $HOME`** (or use `just stow`). Bare `stow <pkg>` from `dot/` targets the
  repo root and silently creates junk symlinks inside the repo.
- Everything else (nix activation form, `lib.hm.dag.entryAfter` on Darwin, docs inside a
  package): `dot/README.md`.

## Zellij — named sessions, and staying usable inside vim

Config in `dot/zellij/`; sessions, autolock, clipboard and keys are in
`dot/zellij/README.md`.

**Nested in tmux, `Ctrl-b` never arrives.** tmux's prefix is `Ctrl-b` too, so it eats the
key and zellij looks frozen. `Ctrl-b Ctrl-b` sends one through, `Ctrl-q` quits zellij, and
`zellij --session <name> action detach` from another pane frees it.

## Searxngr — Privacy-Focused Search

CLI for dungeon's SearXNG; config in `dot/searxngr-config/`, binary via `uv tool install`. See the `/searxngr-search` skill.

## oMLX

Launchd service `org.nixos.omlx` on port 8000, settings generated by
`nixos/modules/darwin/omlx.nix`. `dot/omlx/CLAUDE.md` owns the rest. Its base
`dot/omlx/.omlx/settings.json` is **generated, not committed**: run `just secrets` in
`nixos/` before the first activation on a new host.

## PI WEB — supervise pi sessions from a browser

moria only, at `https://pi.grehg2.xyz` over Tailscale; config in `dot/pi-web/`, module
`nixos/modules/darwin/pi-web.nix`, `just pi-web-setup` once per host. Why nix does not own
its launchd agents: `nixos/CLAUDE.md` → "PI WEB is the exception to the launchd rule above".
PI WEB has **no authentication**. The tailnet is the only thing keeping it private.

## ComfyUI — image generation on moria

FLUX.2 klein on moria's GPU at `https://comfy.grehg2.xyz`, no authentication, tailnet only.
`nixos/CLAUDE.md` → "ComfyUI on moria" runs it; `docs/image-models.md` says why. Agents draw
through `skills/image-generate`; Hermes uses its native `image_generate` tool instead.

## Claude Code in Docker

`claude-docker` (zsh function in `dot/zsh/.zshrc`) bind-mounts your real `~/.claude` and
`~/Git`. See `claude-code/CLAUDE.md`.

## Hermes — runs on dungeon, Desktop clients here

Runs only on dungeon, from `~/Git/home-lab/hermes/`. This repo holds what dungeon mounts
(`hermes/hooks/`, `hermes/skills/`, `skills/`, `bin/`) and
`nixos/modules/darwin/hermes-desktop.nix`, plus the bench. See `hermes/CLAUDE.md`, which also records the
retired harness and where its run log lives.

## Secret Management

All secrets live in 1Password (vault **Infra**). Committed `.tpl` files hold
`{{ op://Infra/Item/field }}` references; `cd nixos && just secrets` renders the gitignored
real files. Never commit plaintext; add the secret to 1Password and reference it.

Never search this repo with `grep -r` or `rtk grep -r`: they read gitignored files, and on
2026-10-30 one printed `DEEPSEEK_API_KEY` from `nixos/secrets/.env` into a transcript. `rg`
skips them.

### Prerequisites

`op` needs the desktop integration per machine; macOS 27 needs an extra grant. moria and
dungeon use a service account token at `~/.config/op/service-account-token` (mode `600`,
reads Infra, can't write). Keep it in that file, never in the environment, because
everything an agent starts inherits the environment. Any process running as Greg can read it.
macOS 27 fix, token rotation and limits: `nixos/docs/secrets.md`.

## Before a pi run — deepseek-preflight

Run `bin/deepseek-preflight.py` before starting DeepSeek work: key funded, peak window,
OpenCode Go quota. Exit 0 clear, 1 needs a human, 2 could not tell. The docstring and
`dot/pi/CLAUDE.md` → "Pricing" carry the reasons and numbers.

## pi's heavy tools are off until you ask — `/enable`, `pi-subagents`

A fresh pi session omits `reddit_*` and `subagent_*` to halve the cold start. `/enable reddit`
or `PI_ENABLE_TOOLS=reddit` turns Reddit on; the `pi-subagents` alias loads subagents. Decide
at session start: enabling later re-prefills the conversation. `dot/pi/CLAUDE.md` →
"Lazy tools" has the mechanism.

## Watching pi Workers — pi-narrate, pi-workers, pi-rpc

`bin/pi-narrate.py`, `bin/pi-workers.py` and `bin/pi-rpc.py` make an `/orchestrate-pi` run
visible and steerable; `-h` documents each. Design: `dot/pi/CLAUDE.md` → "Seeing what an
unattended worker is doing".

## Thread Fetchers — Search & Convert HN & Reddit to Markdown/JSON

`reddit-search.py` and `fetch-thread.py`, no login needed; see the `reddit` skill and
`bin/CLAUDE.md` → "Thread fetchers".

## Local Diff & PR Viewers — diff2html & difit

`dhtml`, `difit`, `gpr`: Mac-only, flags in the root `README.md`, notes in `bin/CLAUDE.md`.


## This repo is public

Nothing private goes in: no secrets, and no details of private repos. Claude Code writes to
`dot/claude/.claude/settings.json` itself (it is `~/.claude/settings.json`); on 2026-10-22 it
added an `autoMode` block describing the private notes vault. Such a block belongs in that
repo's own `.claude/settings.json`. Read that file's diff before committing it.

## NixOS / nix-darwin

See `nixos/CLAUDE.md` for host management, deployment commands, and common mistakes.
