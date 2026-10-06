# Hermes

**Hermes runs only on dungeon**, in Docker, from `~/Git/home-lab/hermes/`. That
directory owns the config, the SOULs, the bot profiles, the transports (Telegram,
email, Slack through Old Gregg) and the secrets. Start there for anything about how
a bot behaves.

What is here is what dungeon mounts from toolbox, plus the measurements behind it:

- `hooks/` and `skills/`: the completion gates and the Hermes-only skills. home-lab's
  compose mounts them by path, so **do not move them**.
- `bench/` is the builder-model race, `seed/` holds task cards, `tests/` tests the gates.

Agent tools are scripts in `bin/` and shared skills are in `skills/`, both also
mounted by dungeon; `skills/README.md` has the convention and who grants what.

## The clients: Hermes Desktop on moria and citadel

Both Macs run the `hermes-desktop` cask as a **client** of dungeon's dashboard at
`https://hermes.grehg2.xyz`, over Tailscale. `nixos/modules/darwin/hermes-desktop.nix`
adds it once, as primary, to Desktop's `connections.json`; sign-in is one manual
step. Setup and the one-time cutover from moria's old server:
`nixos/docs/darwin-post-deploy.md` → Hermes Desktop.

**Never run a messaging gateway on a client.** moria ran its own Hermes, with
Telegram, until 2026-10. Two pollers on one Telegram token each get a random share
of the updates; Slack load-balances events across connections sharing an app token,
so a second consumer steals Old Gregg's messages; two IMAP pollers race for one
mailbox. So no chat token belongs in any file a client Mac reads,
`nixos/secrets/.env` included, since every shell exports it. `just dr` warns while a
gateway agent or a token is still there.

**Home Assistant is read-only by design.** home-lab `hermes/README.md` §8: the `ha_*`
toolset stays off, and the token is not named `HASS_TOKEN` because that name enables
it. `Infra/Hermes/hass_token_pi_harness` (pi's) is *not* read-only: a POST to a bogus
service returns 400, not 401. Never hand it to a bot.

## Why the roster looks like it does

The reasoning lives here because the evidence does (`bench/`); which model each bot
runs is home-lab's config.

**The reviewer must be a different family, and unconditional.** By arXiv 2609.04270,
same-model self-review had the highest error detection and no significant accuracy
gain (it rejected 2.1x as often for a third the repair rate), while a cross-family
mid-tier reviewer gave +12 points at 2% false rejection. And the builder cannot be
trusted to ask for help: recognising you are stuck is the thing a small model cannot
do. Ours had `clarify` and instructions to ask, and published 2,120 false rows
instead. **Writes stay single-threaded**: two agents editing one tree make
conflicting implicit choices.

`bench/quick-ab/` races builder models on three small cards with hidden tests
(`run.py --report <dir>` prints the table). On 2026-09-25 (58 runs), Qwen3.6-35B-A3B
finished a card in about a minute but **declared done with hidden tests failing** in
6 of 9 runs (78% of hidden tests); dense 27B-class models reached 94% at 5–7 minutes.
The same MoE **reviewed by another family** reached 92–94% in about 2.5 minutes, and
DeepSeek reviewed as well as Claude at 1/40th the price. **Kanban's review lane is not
that:** it reruns the card's assignee, so the builder reviews itself.
`skills/verify-agent-output/` puts the review on evidence: a model judging code alone
catches ~45% of real errors, the same model plus deterministic analysis 94%.

The bench drives a local `abtest` profile through the `hermes` CLI, so it needs a
Hermes home with that profile on the machine that runs it.

## The gates

`hooks/require-green.sh` refuses `kanban_complete` and `kanban_request_review` when
the tree would not install for anybody else. Three runs reached a green suite by
deleting `[build-system]` or the dependency list, or by hand-making wrappers in
`.venv`, and the agent, the reviewer and the scorer all read that polluted venv and
agreed. `tests/gate-evasions.sh` replays every bypass that has worked, on the host, in
seconds; its last case asserts an installable tree still **passes**, because a gate
that refuses good work deadlocks an honest agent. It checks the card's own workspace
(`HERMES_KANBAN_WORKSPACE`, else the payload's `cwd`). Each declared console script
must run `--help`. **Known limit:** deleting the scripts table skips that step, and
only the clean sync and the tests still gate the tree.

**It only fires on board-driven work.** A plain Bot Chat never calls either tool, so
for chat-driven work run `bin/installs-from-clean.sh <workspace>` yourself.

`skills/llm-wiki-review/` is Wanderloots' Review Companion v1.0.0, copied verbatim
(sha256 `d9c03763…59dc2c`, matching its QUALIFICATION.md). It calls itself "not
deterministic enforcement"; `hooks/wiki-review-gate.py` is: compiled pages need a
`Review/` proposal whose `decision: approve` the bot did not write itself.
`tests/wiki-review-gate.sh` covers each rule. `terminal` can still write files, so it
is a fence, not a wall. On its first six ingests the local model imagined Greg saying
"approve" and wrote the decision itself, and overwrote a rejected proposal to reopen
it; the gate caught both.

**Hook consent is automatic on dungeon.** Its profiles set `hooks_auto_accept: true`,
so every run approves the hook, including after an edit. Without it, Hermes pins
approval to the script's mtime and an edited hook stops firing until a run with
`--accept-hooks`. `hooks revoke` disables a hook outright, and `hooks test` fires the
script without recording consent.

## Traps that hold wherever Hermes runs

- **A profile's `config.yaml` replaces the root's key by key**: `hooks`,
  `agent.disabled_toolsets`, all of it. A profile carrying one disabled toolset
  dropped the root's other seventeen and advertised 25 tools / 42 KB of schema per
  request instead of 16 / 30 KB. Compare `hermes -p <bot> prompt-size` against
  `default`; any difference is an override.
- **A secondary profile does not fall back to the root `.env`, and an unresolved
  `${VAR}` is sent verbatim** (`_env_ref_lookup`, upstream #84079). The default
  profile reads `os.environ`, so the CLI works while every Bot Chat answers
  `HTTP 401: Invalid API key`. On dungeon each profile resolves `${LITELLM_API_KEY}`
  from its own `.env`. A request dump settles it:
  `Authorization: Bearer ${LITELLM...KEY}` is the literal template.
- **A Telegram chat keeps its system prompt until `/new`.** A gateway restart does
  not start a new session, so a SOUL or skill change is invisible until then.
- **`hermes doctor`'s "No API key found" is a false positive** for `LITELLM_API_KEY`:
  it greps for thirty hard-coded vendor names. **Never `hermes doctor --fix` or
  `hermes setup`** to bump `_config_version`: both rewrite `config.yaml` from parsed
  YAML and drop every comment. Apply the step from `config_migrations.py` by hand.
- **`agent.reasoning_effort` does nothing against oMLX.** It reaches the wire and
  oMLX ignores it (same text, same tokens at `low` and `high`, 2026-09-22). oMLX
  takes effort and `thinking_budget_tokens` per model from its own
  `model_settings.json`, which `nixos/modules/darwin/omlx.nix` deploys.
- **`HERMES_WRITE_SAFE_ROOT` is a security feature.** This project once widened it
  to get past a blocked run and called that a fix.
- **A quiet worker is not a stalled one.** Generation happens in oMLX; judge on its
  CPU, not the client's.
- **An unreachable compression target is a deadline.** If the `protect_last_n`
  messages alone exceed `target_ratio`, every attempt misses and the goal judge
  eventually rules the goal unachievable.
- `provider: custom:omlx` is the old form; it raises `Unknown provider` and the
  worker still exits 0. Use `provider: "custom"` with `base_url` and `api_key`.

`~/Git/notes/ref-hermes-run-log.md` has the run history and every finding.
