# Toolbox

## This repo is public

Nothing private goes in: no secrets, and no details of private repos. Claude Code writes
to `dot/claude/.claude/settings.json` itself (it is `~/.claude/settings.json`) and once
added a block describing the private notes vault; such a block belongs in that repo's own
`.claude/settings.json`. Read that file's diff before committing it.

## Secret Management

All secrets live in 1Password (vault **Infra**). Committed `.tpl` files hold
`{{ op://Infra/Item/field }}` references; `cd nixos && just secrets` renders the gitignored
real files. Never commit plaintext. Setup, the macOS 27 grant and token rotation:
`nixos/docs/secrets.md`.

Search with `git grep`, never `grep -r` or `rtk grep -r`: they read gitignored files and
have printed `DEEPSEEK_API_KEY` from `nixos/secrets/.env` into a transcript. `rg` skips
those files too, but the global `.claude/` ignore also hides `dot/claude/.claude/` from it,
so a hook or the global `CLAUDE.md` can look unreferenced.

## Claude commands, skills and settings

- A `.md` in `claude-commands/` becomes `/<name>` everywhere. The whole directory is
  symlinked into `~/.claude/commands/`, so keep docs out of it (a `README.md` would
  register as `/README`).
- A new skill or agent tool follows `skills/README.md`; `tests/test_skills.py` enforces it.
  `skills/wayfinder/` plans work too big for one session; run `setup-matt-pocock-skills`
  once per target repo.
- Nix hosts get `commands`, `skills`, the global `CLAUDE.md`, `settings.json`, `hooks` and
  the ccstatusline config as symlinks from `nixos/modules/programs/tui/claude.nix`; non-Nix
  hosts run `just setup-claude`. Detail: `nixos/CLAUDE.md` → "Claude Code on each host".
- `link_repo` refuses to overwrite a *real* file and only warns: move the file into
  `dot/claude/.claude/`, delete the original, re-run home-manager.
- The global gitignore ignores `.claude/`, so a new file under `dot/claude/.claude/` needs
  `git add -f`. `tests/test_settings_hooks_tracked.py` fails CI on a hook `settings.json`
  runs but git lacks.
- `settings.json` sets `CLAUDE_CODE_FORCE_SESSION_PERSISTENCE=1`: Claude Code's
  `CLAUDE_CODE_CHILD_SESSION=1` marker leaks into relaunched terminals and silently drops
  transcripts.
- Status line: `dot/ccstatusline/README.md`.

## Dotfiles

Portable, plain-syntax and stow-deployed. A config that needs nix-only bits sources a
small nix-generated `*.local` overlay that no-ops when absent (`~/.zshrc` +
`~/.zshrc.local`); overlays use stable paths (`/run/current-system/sw/...`), never
`${pkgs.*}` store paths. Use `just stow <package>`: a bare `stow <pkg>` from `dot/` targets
the repo root and silently creates junk symlinks. The rest: `dot/README.md`.

## Pointers

- NixOS / nix-darwin hosts, deploys and common mistakes: `nixos/CLAUDE.md`.
- Shell helpers and thread fetchers: `bin/CLAUDE.md`.
- `shims/` holds wrappers that must beat the real tool on `PATH`. `shims/godot` kills a
  `--headless` run after 600 s (`GODOT_TIMEOUT=<s>`, `0` disables).
- Herdr config, keys, hooks and TUI testing: `docs/herdr-config.md`. Never leave Herdr's
  integrations checked on its first-run screen or run `herdr integration install`: they
  write through the symlinks into this repo.
- Hermes runs only on dungeon, from `~/Git/home-lab/hermes/`; this repo holds what dungeon
  mounts: `hermes/CLAUDE.md`.
- pi: `dot/pi/CLAUDE.md`. Its `reddit_*` and `subagent_*` tools are off until `/enable` or
  the `pi-subagents` alias; decide at session start, since enabling later re-prefills.
  Run `deepseek-preflight.py` before DeepSeek work.
- oMLX: `dot/omlx/CLAUDE.md`. Its `settings.json` is generated: run `just secrets` in
  `nixos/` before the first activation on a new host.
- PI WEB (`pi.grehg2.xyz`) and ComfyUI (`comfy.grehg2.xyz`) run on moria with **no
  authentication**; the tailnet is all that keeps them private. `dot/pi-web/CLAUDE.md`,
  `nixos/CLAUDE.md` → "ComfyUI on moria".
- Crit has sharing off and no auth, so it stays on loopback: `docs/crit.md`.
- Voice input (Caps Lock dictation) and login apps: `nixos/CLAUDE.md`. Vorssaint seeds
  its `defaults` once, so a feature-list edit needs the steps in
  `nixos/modules/darwin/vorssaint.nix`.
- Zellij: `dot/zellij/README.md`. Nested in tmux, `Ctrl-b` never arrives; `Ctrl-b Ctrl-b`
  sends one through.
- `claude-docker`: `claude-code/CLAUDE.md`.
- `/upkeep` (`skills/upkeep/`) takes Dependabot, audits, the flake lock and pins to one
  reviewed PR.
