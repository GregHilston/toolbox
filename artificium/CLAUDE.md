# Artificium sandbox

A container for [agent-artificium](https://github.com/officialgr/agent-artificium), a
harness built to run unattended for days and finish with one artifact. Driven by
`bin/artificium-sandbox.sh`; `-h` lists the subcommands. The evaluation that chose it over
pi-autoresearch is `~/Git/notes/ref-long-running-harnesses.md`.

## Why the container is the whole safety story

Artificium's README says it plainly: **it is NOT A SAFE PRODUCT.** No sandbox, no approval
layer. It runs shell commands, and it can modify or delete anything its account reaches —
including its own code and its own API key. A spending limit or a restriction written into
its prompt or its config **cannot** contain it, because it can read and edit both.

So none of the safety here lives inside the agent. All of it is the container.

## The three boundaries

**Filesystem.** Two mounts and nothing else. `/instance` (rw) is the entire Artificium root
— `artificium-code/`, `mind/`, `logs/` — because `config.json` lives under the code
directory and the agent may rewrite its own source. `/reference` (ro) holds snapshots of
`toolbox`, `home-lab` and `notes`. No `$HOME`, no Docker socket, no SSH agent, no
`~/.claude`, no host `~/Git`.

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
fails. The blocked probes target moria's LAN and tailnet addresses on the same port the
gateway hole allows: if either answers, the rules are wrong in the only way that matters.
A firewall that is not asserted is a firewall that is assumed.

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

- The oMLX key travels as an environment variable so it never appears in `ps`, but `setup`
  still writes it to `/instance/artificium-code/.secrets.json`, which is on the host bind
  mount. An oMLX **sub-key** (`auth.sub_keys` in `dot/omlx/.omlx/settings.json.tpl`) makes
  that credential revocable without rotating the one every other tool here uses. oMLX admin
  routes are gated on `secret_key`, not the api key, so an inference key cannot reconfigure
  the server — the exposure is use of the GPU, not control of it.
- The pinned Artificium commit is a `Dockerfile` build arg. Artificium also has its own
  `upgrade` command, which the agent can run against GitHub; if it does, the image pin and
  the instance no longer agree.

## Model

`Qwen3.6-35B-A3B-4bit-DWQ`, whose `model_settings.json` entry carries the run's context
bound. Chosen over the dense `Qwen3.8-27B-4bit` for two reasons that only apply when nobody
is watching: it is 4.5× faster in wall-clock, which is the currency of an unattended run,
and it has no `reasoning_effort` knob — the setting that, left at its Qwen3.8 default, burns
a whole token budget and emits no answer at all. `dot/omlx/CLAUDE.md` has the measurements.
