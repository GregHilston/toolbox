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

A `claude-skills/<name>/SKILL.md` with `name`/`description` frontmatter becomes
`/<name>`. Copy an existing skill for the shape.

### How they reach each host

**Nix-managed hosts** (NixOS / nix-darwin): automatic. The home-manager module at
`nixos/modules/programs/tui/claude.nix` creates the symlinks during `home-manager`
activation when you run `just fr <host>` or `just dr <host>`. It now manages six
targets, all symlinked into this repo (so they're version-controlled and deploy to
every host that imports `programs/tui`):

- `~/.claude/commands`     → `claude-commands/`
- `~/.claude/skills`       → `claude-skills/`
- `~/.claude/CLAUDE.md`    → `dot/claude/.claude/CLAUDE.md`   (global, cross-repo memory)
- `~/.claude/settings.json`→ `dot/claude/.claude/settings.json` (permissions, hooks, plugins)
- `~/.claude/hooks/`       → `dot/claude/.claude/hooks/`      (e.g. the RTK rewrite hook)
- `~/.config/ccstatusline/settings.json` → `dot/ccstatusline/…` (status line layout)

The symlinks are **writable** (they point into the repo, not `/nix/store`) so Claude's
own runtime writes to `settings.json` still work — those just show up as git diffs to
commit or discard.

**Clobber guard:** the activation's `link_repo` helper refuses to overwrite a *real*
file. If a host already has, say, a hand-written `~/.claude/settings.json`, activation
prints a `WARNING` and leaves it untouched. To bring it under management: move that file
into `dot/claude/.claude/`, delete the original, then re-run home-manager.

**Non-Nix hosts**: run `just setup-claude` once after cloning. Since everything is a
symlink into the repo, pulling new commits picks up changes without re-running setup.

### Status Line — ccstatusline

[ccstatusline](https://github.com/sirmalloc/ccstatusline) renders the status line
(context used/window/%, weekly quota, git state). Wired up by `statusLine` in
`dot/claude/.claude/settings.json`; layout in `dot/ccstatusline/`, symlinked by the
same activation as `~/.claude` so it stays writable — run `ccstatusline` bare to open
its TUI, then commit or discard the diff.

Version pin and the `~/.npm-global` install live in `nixos/modules/programs/tui/claude.nix`
(`ccstatuslineVersion`); bump there. It needs `node` on `$PATH`, hence `nodejs_22` in
`nixos/config/base-packages.nix`.

**Widget choices, and why:**

- `context-bar` alone, not `context-length` + `context-window` + `context-percentage`
  beside it. The bar already renders `342k/1.0M (34%)`, so the other three only repeat it.
- The plain `Context %` widget, never the "usable" variant — that one assumes an
  auto-compact cutoff, and we run `autoCompactEnabled: false`.
- `current-working-dir` (segments: 1) and `git-worktree`, so a glance identifies *which*
  session you're typing into. With many concurrent sessions the git widgets alone show
  `master` almost everywhere, and a worktree is indistinguishable from the main checkout.
- A `custom-command` widget on **a line of its own**, running
  `pi-workers.py --from-statusline --oneline`, so an `/orchestrate-pi` run is
  visible without asking Claude: `pi 5w 2▸ 1~ 1✓ $0.0912 ⚠1 stalled`.
  The dedicated line is not cosmetic — ccstatusline does **not** drop a
  separator adjacent to a widget that renders nothing, so putting it inline left
  either a dangling `|` when idle or no gap when active. On its own line the
  whole row disappears when the script prints nothing, which is every session
  that is not orchestrating. Verified by rendering both states, per the advice
  at the end of this section. The script must also never exit non-zero in this
  mode: ccstatusline renders `[Exit: N]` in the bar if it does.
- `weekly-usage` (the `weekly_all` quota) and `session-usage` (the 5-hour block).
  **Not** `weekly-opus-usage` / `weekly-sonnet-usage`: ccstatusline reads
  `https://api.anthropic.com/api/oauth/usage`, which now returns `seven_day_opus: null`
  and `seven_day_sonnet: null` — there is one combined weekly limit, no per-model split.
  ccstatusline maps a null bucket to `0` rather than "absent", so those two widgets sit
  at a permanent `0.0%` instead of hiding. Curl that endpoint with the OAuth token from
  the `Claude Code-credentials` keychain item to see what your plan actually reports.

Deliberately **not** enabled: powerline mode needs a Nerd Font present on every host
(NixOS, darwin, Termux), which is a poor trade for a repo whose point is uniform deploys.
To audit the other ~80 widgets, render them against a real session rather than guessing —
pipe a Claude Code status payload into `ccstatusline` with `HOME` pointed at a throwaway
config dir, so your live line is untouched.

## Voice Input — Hold Caps Lock to Dictate

Caps Lock: a tap sends Escape, a hold sends F18, which [Handy](https://handy.computer/)
transcribes locally. Karabiner-Elements does this on macOS (`dot/karabiner/`), `services.keyd`
on NixOS GUI hosts.

Launching, permissions, and why the app's own "launch at login" stays off are all in
`nixos/CLAUDE.md` → "Launching GUI apps at login", which owns this.

## Menu Bar — Ice

[Ice](https://github.com/jordanbaird/Ice) manages the macOS menu bar. Cask in
`modules/darwin/homebrew-base.nix`, launched by `modules/darwin/ice.nix` — same
launchd pattern as Handy, documented in `nixos/CLAUDE.md`.

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

## Searxngr — Privacy-Focused Search

CLI for dungeon's self-hosted SearXNG instance. Config managed via stow (`dot/searxngr-config/`), binary installed via `uv tool install`. See `/searxngr-search` skill for Claude Code integration.

## oMLX

Local LLM inference (Apple Silicon), launchd service `org.nixos.omlx` on port 8000.
Per-host settings are generated by `nixos/modules/darwin/omlx.nix`, not stowed.

`dot/omlx/CLAUDE.md` owns per-model settings, model variants, and restart
troubleshooting. Note its merge base `dot/omlx/.omlx/settings.json` is **generated,
not committed** — run `just secrets` in `nixos/` before the first activation on a new
host, or the merge has nothing to read.

## PI WEB — supervise pi sessions from a browser

[PI WEB](https://pi-web.dev/) keeps pi coding-agent sessions alive in real
workspaces, so they can be driven from a phone or tablet instead of a terminal.
**moria only** — it is the 128GB box and already runs oMLX, so sessions and
inference stay together. Reachable at `https://pi.grehg2.xyz` over Tailscale.

Config in `dot/pi-web/`; the nix module is
`nixos/modules/darwin/pi-web.nix`. Installed once per host with
`just pi-web-setup` in `nixos/` — nix deliberately does not own its launchd
agents, and `nixos/CLAUDE.md` explains why.

PI WEB has **no authentication**. The tailnet is the only thing keeping it
private.

## Claude Code in Docker

`claude-docker` (a zsh function in `dot/zsh/.zshrc`) runs Claude Code in a container
that bind-mounts your real `~/.claude` and `~/Git`, so credentials and sessions are
shared. See `claude-code/CLAUDE.md`.

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

`op` needs the 1Password desktop integration enabled per machine (Settings → Developer
→ "Integrate with 1Password CLI").

On **headless dungeon** that integration is GUI-gated, so `op inject` fails with
`authorization timeout`. Put a 1Password **service account token** (Business/Teams
plan) at `~/.config/op/service-account-token`, mode `600` — `just secrets` picks it up
and needs no GUI. Without one, VNC in and unlock 1Password first.

## Before a pi run — deepseek-preflight

`bin/deepseek-preflight.py` answers "is it a good moment to start" in one call:
is the key funded (default floor $2), and is DeepSeek in a peak window (double
rate, 01:00–04:00 and 06:00–10:00 UTC Mon–Fri — which is 21:00–00:00 Eastern
Sun–Thu, exactly when an overnight run gets started). Exit 0 clear, 1 needs a
human, 2 could not tell.

Both checks exist because a run died on a `402` mid-flight and three workers
were killed with their work uncommitted, while still reporting completion.
`dot/pi/CLAUDE.md` → "Pricing" carries the numbers.

## Watching pi Workers — pi-narrate, pi-workers, pi-rpc

`bin/pi-narrate.py` (pi's JSON event stream → one readable line per event),
`bin/pi-workers.py` (every worker's status file → a table, a status-bar line, or
JSON) and `bin/pi-rpc.py` (steer a worker that is still running). Together they
are why an `/orchestrate-pi` run is no longer a black box; `-h` documents each.

`dot/pi/CLAUDE.md` → "Seeing what an unattended worker is doing" owns the design
and the reasoning. The short version: workers were spawned with their stdout
redirected to a file, Claude Code captures background output from a PTY, and so
the TUI reported "no output available" for entire runs while pi was emitting a
detailed event stream the whole time.

## Thread Fetchers — Search & Convert HN & Reddit to Markdown/JSON

`reddit-search.py "<query>"` finds threads; `fetch-thread.py <url>` prints a Reddit
or Hacker News thread as markdown (`--format json` for JSON). `-h` has the full
reference for both.

**Reddit needs auth** — it has required it on `.json` endpoints since mid-2026. Both
tools read the same cookie as pi's reddit tools; a 403 means logging in to reddit.com
**in Firefox** and running `bin/reddit-cookie-sync.sh`. See `dot/pi/CLAUDE.md`.

**Reddit's JSON search is dead, which is why `reddit-search.py` scrapes
old.reddit.com instead.** `search.json` does not fail — it answers HTTP 200 with an
empty `children` array, so callers just see "no results". That silently takes out
pi's `reddit_search`, `reddit_pack` and `reddit_trends`, which call the same
endpoint. `reddit-cookie-sync.sh` still reports OK because it probes a *listing*
endpoint, so a healthy cookie is not evidence that search works. Listing endpoints
and thread permalinks are unaffected.

## Local Diff & PR Viewers — diff2html & difit

`dhtml`/`dhtmls`/`dhtmlside` (diff2html), `difit` (PR-like UI), `gpr` (current branch
as a PR diff). Mac-only; flags are in the root `README.md`.

One divergence worth knowing: our `difit.sh` defaults a missing target to `.` (all
uncommitted changes) where upstream would show the last commit.

## NixOS / nix-darwin

See `nixos/CLAUDE.md` for host management, deployment commands, and common mistakes.
