# Agent sandbox

A cage for [Hermes Agent](https://hermes-agent.nousresearch.com/docs) driven by
`hermes kanban`: a durable SQLite task board whose dispatcher spawns one OS process per
card, with an agent-to-agent review gate. Driven by `bin/agent-sandbox.sh`; `-h` lists the
subcommands. Scored by `bin/agent-bench.py`, watched in flight with `bin/agent-watch.py`, re-checked
from a clean tree and pushed to a phone by `bin/agent-deliver.sh`, and **verified by
`bin/agent-verify.sh` before any long run**.

**Hermes is the only harness here.** The alternative that was evaluated alongside it lost
the head-to-head and its code is gone; `~/Git/notes/ref-artificium-vs-hermes-kanban.md`
keeps that record, and git history has the code if it is ever wanted back. Nothing in this
directory should need it.

## Verify before you run

`bin/agent-verify.sh` asserts the mechanisms actually fire — toolset pruning, the model
split, the skills, and the completion gate blocking a red suite. Run 2 burned 75 minutes on
a config whose headline change was silently inert (auxiliary slots with no `base_url` fall
back to the main model, with no error anywhere). Static inspection cannot catch that; only
watching the mechanism fire can. **Three minutes here saves an hour.**

## Why Kanban and not Bot Mode

The Hermes feature everyone demos is Bot Mode group rooms, and they cannot drive an
unattended run: a hard cap of **10 messages per send and 3 rounds**, not configurable, and
**no CLI at all** — Desktop or raw API only. Headless, they do not exist.

`hermes kanban` is the headless primitive that does. Its dispatcher ticks inside the gateway
(the standalone `kanban daemon` is deprecated and refuses to start without `--force`, because
the two race for claims), spawns `hermes -p <assignee>` per card in an isolated workspace,
and runs the review cycle — `kanban_request_review` → a reviewer profile is spawned →
`request_changes` or `complete` — with no human in it.

It also has stall detection by construction: per-card `max_retries`,
protocol-violation detection when a worker exits without a terminal kanban call, terminal
provider errors blocking on first occurrence, and a heartbeat reclaim.

## Four configuration traps, each of which cost an hour

All four present as *the model failing*, which is why they are written down.

- **`provider: custom:omlx` is not valid here.** That is the v39 `providers:`-block form
  `home-lab/hermes` uses. This release wants plain `provider: "custom"` with `base_url` and
  `api_key` inline. The wrong value raises `Unknown provider` — and the worker process still
  **exits 0**, so the dispatcher records "clean exit without calling a terminal kanban tool"
  and the board fills with protocol violations that look exactly like a small model failing
  to drive an agent loop. It is not. Test with `hermes -p <profile> -z "say pong"`.
- **`_config_version` must match the release** (v0.21.3 = 44). Absent, the file parses as v0
  and whole sections are ignored in silence; only `hermes doctor` mentions it.
- **`profile create` snapshots the root model block.** Fixing the root config does not reach
  a profile that already exists. `bootstrap.sh` re-stamps every profile on every boot.
- **`AGENT_OFFLINE=1` used to make the card unsatisfiable.** The image shipped an empty
  uv cache and no pytest, so with the internet gone `uv run pytest` and `uv run vt-smb
  build` — criteria 1 and 2 of the card's DONE WHEN, and both of the commands
  `require-green.sh` runs — could not resolve a single dependency. Each attempt burned
  ~50s retrying PyPI and then failed, so two iterations were written off as src-layout
  packaging failures that were nothing of the kind. The Dockerfile now resolves the seeded
  dependency set at build time, ships the resulting `uv.lock` beside the seeded
  `pyproject.toml`, and the entrypoint exports `UV_OFFLINE=1` so a package that is genuinely
  missing fails fast and names itself. `agent-verify.sh` section 4 asserts all of it.

`max_in_progress: 1` on purpose: what is being tested is durable structure, not parallelism,
and two workers contending for moria's single GPU would confound the comparison.

## Why the container is the whole safety story

Hermes ships no sandbox and no approval layer. It runs shell commands, and it can modify or
delete anything its account reaches — including its own config. A restriction written into
its prompt or its config **cannot** contain it, because it can read and edit both. The
`pre_tool_call` gate is the one exception, and only because it lives outside the model's
reach.

So none of the safety here lives inside the agent. All of it is the container.

## The three boundaries

**Filesystem.** Two mounts and nothing else. `/instance` (rw) holds the whole run:
`workspace/` is the tree the agent builds and `home/` is `HERMES_HOME` — the kanban board,
the profiles, the logs — both on the bind mount so they survive a restart and stay readable
from the host while a run continues. `/reference` (ro) holds snapshots of `toolbox`,
`home-lab` and `notes`. No `$HOME`, no Docker socket, no SSH agent, no `~/.claude`, no host
`~/Git`.

`/instance` is a host bind mount rather than a named volume, which the README's "do not
expose host drives" line argues against. The deviation is deliberate: the directory is
created empty for the run, its blast radius is exactly itself, and the dataset and scripts —
the point of the whole exercise — need to be readable without `docker cp`.

**Network.** `init-firewall.sh` installs default-DROP egress: the public internet is
allowed, every private range is not, and oMLX is reached through a single `host-gateway/32`
hole on one port.

`100.64.0.0/10` is in the deny list and is the rule that matters most. The tailnet is the
path that reaches every other machine on the network, and a rule set that denies only
RFC1918 misses it entirely. IPv6 is dropped outright rather than mirrored, because left open
it is a trivial detour around all of the above.

The script then **asserts its own work** and refuses to start the agent if any assertion
fails. A firewall that is not asserted is a firewall that is assumed — but an assertion that
cannot fail is worse than none, because it reads as coverage. Two mistakes were made here
and are worth not repeating:

- The blocked probes were hardcoded to addresses that answered nothing (a stale LAN alias
  and a tailnet IP whose daemon was stopped), so they printed PASS regardless of the rules.
  They are now derived by the launcher from this host's live addresses, and the launcher
  **verifies each one answers from the host** before the container starts. The primary
  probe is this host's own oMLX by its LAN address: live, and the same service the gateway
  hole allows.
- The check treated any non-zero `curl` exit as "blocked", scoring a refused connection —
  one whose packet reached the target — the same as a dropped one. It now requires exit 28
  specifically, and separately asserts each deny rule with `iptables -C`, which tests the
  ruleset rather than the network's current mood.

**Privilege.** Root exists only long enough to install the rules and seed a fresh instance,
then `gosu` drops to a non-root user for the rest of the container's life. With
`no-new-privileges`, no `sudo` in the image, and `--cap-drop=ALL` plus the few capabilities
the entrypoint needs, the agent cannot undo the firewall that constrains it.

Resource caps (`--memory`, `--pids-limit`, `--cpus`) are not about the agent misbehaving;
they stop agent-authored code from starving the oMLX server the agent itself depends on.

## The read-only reference tree

`export-reference` builds it with `git archive HEAD` per repo. That excludes every gitignored
path **by construction** rather than by a blocklist that goes stale — `nixos/secrets/.env`
and its seven live keys, `home-lab/roger/secrets/.env`, `.venv`, `.worktrees`. Pathspecs
handle the one `.env` that is tracked, in `home-lab`: no credentials in it, but home-network
topology all the same.

Read-only is not the same as harmless. The agent has internet egress, so anything in that
tree is something it could send somewhere. That is the reason the export is a filtered
snapshot of committed history and not a `:ro` bind of the live directories.

## Known residue

- **The agent is handed a working oMLX key, and an oMLX key is not inference-only.**
  `POST /v1/models/{id}/load` and `/unload` take `Depends(verify_api_key)` — the plain
  inference key — and `admin/routes.py`'s `_require_admin_or_bearer` accepts a Bearer key
  for the admin load route too. So the agent can evict a 19 GiB model out from under pi.
  Only the settings-changing routes are gated on `secret_key`. An oMLX **sub-key**
  (`auth.sub_keys` in `dot/omlx/.omlx/settings.json.tpl`) narrows *revocation*, not
  capability — it is still worth having, and the launcher warns when the shared key is used,
  but do not mistake it for a capability boundary.
- The key travels as an environment variable so it never appears in `ps`, but `bootstrap.sh`
  writes it to `${HERMES_HOME}/.env` — `/instance/home/.env`, on the host bind mount. The
  agent has arbitrary shell and unrestricted egress, so any key it holds is a key it can
  send anywhere.
- The Hermes version is pinned in the `FROM` line, currently `v2026.9.14`. Nothing stops the
  agent installing a different one inside a running container, in which case the image pin
  and the instance no longer agree.
- **The privilege boundary is one layer deep.** `no-new-privileges` is the only thing
  stopping the agent from recovering uid 0 through a setuid binary in the base image and
  flushing the rules, since the container keeps `NET_ADMIN` in its bounding set for its whole
  life. The mechanism is correct, but it is alone. The next hardening step is to split the
  run: a short-lived container installs the rules and exits, and the agent joins its network
  namespace with `--network=container:<fw> --cap-drop=ALL`, so regaining root buys nothing.
  Deliberately deferred until a run has proven itself end to end.

## Why moria, and only moria

Long runs need 34 GB of resident models (19 GB builder + 15 GB judge). dungeon has
36 GB total while running Frigate and ~60 containers behind a ~27 GB oMLX ceiling, and the
A3B is already measured as not fitting beside Frigate's vision model. Running the agent on
dungeon against moria's oMLX does not help — moria still has to be awake, which is the
actual constraint. dungeon's Hermes stays what it is: quick questions against the notes
vault.

**moria sleeps.** `pmset sleep` is 1 minute, and runs so far have survived only because
Amphetamine happened to be holding an assertion. Wrap long runs in `caffeinate -dims`, and
keep the lid open — clamshell still sleeps.

## Model

`Qwen3.6-35B-A3B-4bit-DWQ`, whose `model_settings.json` entry carries the run's context
bound. Chosen over the dense `Qwen3.8-27B-4bit` for two reasons that only apply when nobody
is watching: it is 4.5× faster in wall-clock, which is the currency of an unattended run,
and it has no `reasoning_effort` knob — the setting that, left at its Qwen3.8 default, burns
a whole token budget and emits no answer at all. `dot/omlx/CLAUDE.md` has the measurements.

DWQ rather than the plain `Qwen3.6-35B-A3B-4bit` that pi defaults to, and the price is
**~10%** — paired measurement says -9.8% decode, -9.3% prefill, against the 21% this repo
quoted for a year from sequential runs that were really measuring their own thermal drift.
The two checkpoints differ in precision layout, not in learned scales: the plain build is
`bits: 4` with the MoE gates at 8, DWQ is `bits: 8` with only the expert FFNs at 4, so it
runs embeddings, `lm_head`, the gates and the whole attention stack at 8-bit. For an
unattended run a certain 10% is a good trade against an uncorrected derailment; for pi, with
a human present, it is not. `AGENT_BUILD_MODEL` overrides it for an experiment, and
`agent-verify.sh` section 4 asserts the builder actually *answers* on the expected model
rather than merely naming it in a config file.
