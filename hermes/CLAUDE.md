# Hermes

Bots on moria, against local inference. **A Bot is a profile** — the docs are
explicit that it is "isolated config, memory, skills, credentials and chat
history under `~/.hermes/profiles/<name>/`" — so the directories here and the
roster in the Desktop app are the same objects seen from two ends.

`ls` answers what is in here. `nixos/modules/programs/tui/hermes.nix` symlinks
`config.yaml`, `hooks/` and each `profiles/<bot>/SOUL.md` into `~/.hermes`.

## There are two Hermes deployments — check before wiring anything

`~/Git/home-lab/hermes/` runs one on **dungeon**, reached over **Slack (through Old
Gregg) and email at grehgpi@**. This one, on **moria**, takes **Telegram**.

**They must not share an integration.** Slack load-balances events across
connections sharing an app token, so a second consumer steals a random share of
Old Gregg's messages rather than adding a listener; two IMAP pollers race for
the same mail. Both were briefly configured here on 2026-09-22.

**Home Assistant is the sharpest edge.** `home-lab/hermes/README.md` §8: the
`ha_*` toolset "is deliberately not enabled, and the token is not named
`HASS_TOKEN` because that name would enable it" — HA has no per-entity
permissions and the locks are S2 Authenticated, so read-only is the whole
design. `Infra/Hermes/hass_token_pi_harness` is *not* read-only: a POST to a
bogus service returns 400, not 401, so it clears auth and can call services.
If moria ever needs HA, it wants its own token from the read-only `hermes` user.

## Installing it

The `hermes-desktop` cask stages an **installer**, not the app: `Hermes.app`
holds one `Hermes-Setup` binary and no CLI. `open -a Hermes` once, then reload
the shell — the installer puts the binary at `~/.local/bin/hermes` and edits
your rc. `just dr` alone leaves you with `command not found: hermes`.

The gateway service is then `hermes gateway install` by hand, and transports are
`hermes gateway setup`. Full checklist: `nixos/docs/darwin-post-deploy.md`.

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

## The gate only fires on board-driven work

`hooks/require-green.sh` matches `^kanban_(complete|request_review)$`. A plain
Bot Chat never issues either, so **the gate does nothing in conversation** — it
guards work handed off through `hermes kanban`. For chat-driven work the
equivalent is running `bin/installs-from-clean.sh <workspace>` yourself, or
giving a bot a skill that does.

Each bot carries its own copy of the `hooks` block in
`profiles/<bot>/config.yaml`, because a profile does **not** inherit the root
config's. The root carried it for seven runs and the gate never fired once.

## Traps

- **`${VAR}` in `config.yaml` resolves against the profile's own `.env`, not
  your shell.** `api_key: ${OMLX_API_KEY}` with the key only in
  `nixos/secrets/.env` means every model call goes out keyless and oMLX answers
  `HTTP 401: Invalid API key`. The gateway is a launchd agent; it inherits
  nothing. Credentials the setup wizard can see in your environment are not
  credentials the gateway has — that is also why it reported Slack and Telegram
  configured while `channel_directory.json` held no platforms at all.
- **`~/.hermes/.env` is generated** from `hermes/.env.tpl` by `just secrets`, so
  `hermes config set` writes and anything the wizard stores there are
  overwritten. Put keys in the template.

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
