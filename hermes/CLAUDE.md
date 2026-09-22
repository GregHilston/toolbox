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

## A profile's config REPLACES the root's, key by key

Not just `hooks` — every key. `profiles/<bot>/config.yaml` carried
`agent.disabled_toolsets: [homeassistant]`, which dropped the root's other
seventeen on the floor: `web`, `browser`, `x_search` and the rest were
advertised to every bot, including the ones that run with no network. The cost
was 25 tools / 42.2 KB of schema per request against `default`'s 16 / 30.0 KB.

So each profile now carries the whole list, and the way to see it is to compare
a bot against the root:

```bash
for p in default builder researcher reviewer; do
  hermes -p $p prompt-size | grep "Tool schemas"
done
```

`default` reads the root config alone. **Any profile that differs from it has
overridden something**, and the four numbers agreeing is the check that a
profile's copy is still complete.

## Reading a bot's conversations

They are in `~/.hermes/state.db`, and nowhere else. Read them rather than asking
for a paste:

```bash
sqlite3 -header -column ~/.hermes/state.db \
  "select id, source, display_name, datetime(started_at,'unixepoch','localtime'), message_count
     from sessions order by started_at desc limit 10;"

sqlite3 ~/.hermes/state.db \
  "select role, tool_name, substr(replace(coalesce(content,''),char(10),' '),1,200)
     from messages where session_id='<id>' order by id;"
```

`source` tells the surface apart: `telegram`, `desktop`, `cli`. There are
`messages_fts` and `messages_fts_trigram` indexes if you want to search rather
than scroll.

The two neighbouring paths are decoys. `~/.hermes/sessions/sessions.json` says
so in its own `_README` — it is a legacy mirror of the gateway *routing* index,
a map of session keys to ids, with no message text. `~/.hermes/logs/` is the
gateway's operational log: it records that a Telegram message arrived and how
many characters the reply was, never what either said.

Runtime state, so none of it is in git.

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
- **`hermes doctor`'s "No API key found in ~/.hermes/.env" is a permanent false
  positive here.** It greps the file for one of thirty hard-coded vendor names
  (`doctor.py:_PROVIDER_ENV_HINTS`) and `OMLX_API_KEY` is not among them. The
  key is wired through `config.yaml`'s `api_key: ${OMLX_API_KEY}`; the check
  that actually answers the question is the same doctor's "auxiliary task
  routing resolves: … custom@127.0.0.1".
- **Never `hermes doctor --fix` or `hermes setup` to bump `_config_version`.**
  Both end in `_persist_migration`, which rewrites `config.yaml` from parsed
  YAML — every comment in it is why a setting is what it is, and they do not
  survive. Read the step in `hermes_cli/config_migrations.py`, apply what it
  does by hand, and edit the number.

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
- **`agent.reasoning_effort` does nothing on this setup.** Hermes does put it on
  the wire — a captured request body to `127.0.0.1:8000/v1/chat/completions`
  carries `"reasoning_effort": "low"` — and oMLX ignores it. Measured
  2026-09-22: the same prompt at `low` and at `high` returned the same text,
  the same 400 completion tokens, and an empty `reasoning_content` both times.
  oMLX applies reasoning effort from **its own** `chat_template_kwargs`, per
  model, in `~/.omlx/model_settings.json`, and the DWQ entry the builder runs
  has none — while `Qwen3.8-27B-4bit` has `reasoning_effort: medium` under a
  comment calling it "THE most important setting for this model". What bounds
  thinking for both is `thinking_budget_tokens: 8192` in the same file. So the
  knob is oMLX's, not Hermes'; `nixos/modules/darwin/omlx.nix` generates it.
  Leave the DWQ entry alone without a reason: no `chat_template_kwargs` is the
  configuration that scored 10/10 on our coding eval, the best of anything
  tested.
- `provider: custom:omlx` is the old form. This release wants plain
  `provider: "custom"` with `base_url` and `api_key` inline; the wrong value
  raises `Unknown provider` and the worker still exits 0.

`~/Git/notes/ref-hermes-run-log.md` has the run history and every finding.
