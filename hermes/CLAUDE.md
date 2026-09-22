# Hermes

Bots on moria, against local inference. **A Bot is a profile** — the docs are
explicit that it is "isolated config, memory, skills, credentials and chat
history under `~/.hermes/profiles/<name>/`" — so the directories here and the
roster in the Desktop app are the same objects seen from two ends.

`ls` answers what is in here. `nixos/modules/programs/tui/hermes.nix` symlinks
`config.yaml`, `hooks/` and each `profiles/<bot>/SOUL.md` into `~/.hermes`.

## The symlinks are writable on purpose

Hermes' own configuration docs say `config.yaml` "is not safe to make read-only
for production deployments", and `SOUL.md`, `skills/` and `memories/` are
agent-modified at runtime. So these point into the repo, not `/nix/store`, and
a bot's runtime edits show up as git diffs to commit or discard — the same trade
`claude.nix` makes for `~/.claude/settings.json`.

**A bot can therefore write into this repo.** Worth knowing before pointing an
unsupervised one at it. Only the declarative half is linked; `memories/`,
`sessions/`, `state.db`, `cron/` and `logs/` stay where Hermes puts them.

## What is ours rather than Hermes'

`hooks/require-green.sh` refuses `kanban_complete` and `kanban_request_review`
when the tree would not install for anybody else. It exists because three runs
reached a green suite by deleting the things that make a tree reproducible —
`[build-system]`, the dependency list, and in one case hand-made wrapper
executables in `.venv` — and the agent, the reviewer and the scorer all read
that same polluted venv and all three agreed. `tests/gate-evasions.sh` replays
every bypass that has worked, on the host, in seconds; its last case asserts a
genuinely installable tree still **passes**, because a gate that refuses good
work deadlocks an honest agent.

Everything else this repo once wrapped around Hermes — a container, a Telegram
bot, a run loop, a scorer, a preflight — has been deleted, because Hermes ships
a Docker terminal backend, native Telegram and eighteen other transports, the
kanban board, and an approvals system. See the root `CLAUDE.md`.

## Traps

- **`HERMES_WRITE_SAFE_ROOT` is a security feature**, not a bug. It confines
  writes to a directory. This project once widened it to work around a blocked
  run and wrote that up as a fix.
- **A quiet worker is not a stalled worker.** Generation happens in oMLX on the
  host; the container or client only waits. Judge on oMLX's CPU, never the
  client's.
- **An unreachable compression target is a deadline.** `protect_last_n` exempts
  messages from compression; if those alone exceed `target_ratio`, every attempt
  misses and the goal judge eventually rules the goal unachievable. See
  `config.yaml`.
- `provider: custom:omlx` is the old form. This release wants plain
  `provider: "custom"` with `base_url` and `api_key` inline; the wrong value
  raises `Unknown provider` and the worker still exits 0.

`~/Git/notes/ref-hermes-run-log.md` has the run history and every finding.
