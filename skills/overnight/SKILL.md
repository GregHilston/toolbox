---
name: overnight
description: Work a repo's GitHub issues unattended overnight, one fresh claude or pi process per issue, with ./verify.sh deciding what stays. Use when Greg wants agents to build while he is away. Set the repo up with agent-ready first; for an attended run use /orchestrate.
disable-model-invocation: true
argument-hint: "claude|pi [--model <id>]"
license: MIT
---

# Overnight

One command, already on `PATH`. Run it in your shell (the `terminal` tool in
Hermes, Bash in Claude Code, `bash` in pi) from the repo root, exactly as shown:
no `python3` in front and no directory.

```bash
overnight-loop.py --harness pi                                   # DeepSeek via the gateway's `cloud`, Claude plans and reviews
overnight-loop.py --harness pi --budget 3 --off-peak             # hard $3 cap via LiteLLM, cheap hours only
overnight-loop.py --harness pi --model cloud --board 1           # also keep GitHub project 1 in sync
overnight-loop.py --harness pi --model deepseek/deepseek-flash   # DeepSeek directly; needs DEEPSEEK_API_KEY
overnight-loop.py --harness claude --yolo                        # Claude workers; only inside a container or VM
overnight-loop.py --help                                         # every cap and default
board-sync.py --create "<repo name>"                             # once per repo: make the kanban board
```

Why a script and not you: an orchestrator that is itself a model session fills
its context over a night and compacts. The script holds no context, starts every
worker clean, and trusts `./verify.sh`, never a worker saying it is done.

For each issue a reviewer, Claude by default and from another model family than
DeepSeek on purpose, writes a plan, and reviews the work once it passes the gate.
When it asks for changes, one fresh worker makes them and the gate runs again.
If that fix pass fails the gate, the loop keeps the green work from before it
and says in the issue that the findings are not addressed. A review with no
`VERDICT:` line parks the issue. A reviewer that runs out of money or hits its
usage limit is dropped for the rest of the night, and later issues go
unreviewed; the summary says from which issue.

The gate is `./verify.sh` as the issue's base had it: a worker that changes
`verify.sh` or `tests/baseline_count`, or leaves the run's branch, has its
issue parked. A `./verify.sh` slower than `--verify-minutes` (default 15)
counts as a fail. After each worker and each gate run, the loop kills
processes started meanwhile that have no terminal and run in the repo.

pi workers use the LiteLLM gateway's `cloud` model unless `--model` names
another. When Greg names a spend ("at most $3"), pass it as `--budget`: the
loop stops starting issues once this run has spent that much on the gateway.
The gateway's daily cap on `cloud` is the hard limit underneath: past it,
every request is refused. `--max-cost` (default $60) still applies alongside.
A direct `deepseek/` model needs `DEEPSEEK_API_KEY`, and the loop refuses to
start when that key's balance is under $2.

`--off-peak` works only in DeepSeek's half-price hours: it waits from 20
minutes before peak until peak ends, then carries on until `--hours` is up.
Weekends are off-peak all day; on a weeknight the off-peak windows are short.

## Before starting

Check these with Greg, then start it, and stop there:

1. **The repo passes agent-ready.** The script refuses to start without an
   executable `./verify.sh` that passes, with a dirty tree, or on a branch
   other than the default (pass `--base <branch>` to start from another). It
   then asks the worker's and the reviewer's model for one word, and stops
   with their error if either cannot answer.
2. **The queue.** Open issues with the label (default `ready-for-agent`; pass
   `--label prep:ready` after `/prep`). Each needs a checkable `Done when`.
3. **The caps.** Defaults: 8 hours, 20 issues, 3 parks in a row, 90 minutes per
   agent run, and $60 a night (pi priced from DeepSeek's table, Claude by its own report).
4. **The sandbox.** pi workers run with bash-guard off, and the loop gives
   them the write tool inside the repo through a git-excluded
   `.pi/extensions/pi-permission-system/config.json` (a repo that commits its
   own keeps it). pi's own write tool is refused outside the repo, but its
   bash reaches anything, and `--yolo` turns Claude's permissions off. Run
   either inside a container or VM that mounts only this repo.
5. **Detach it.** Run it in `tmux new -d -s overnight '…'`, not as a harness
   background task, which dies with the session.

`touch .overnight/STOP` ends the run after the current issue; the next run
clears it. Ctrl-C, or closing the tmux session, stops the worker, resets its
unjudged work, takes `overnight:working` off the issue and prints the summary.

## In the morning

The script prints which issues it finished and which it parked, any commit
subjects that are not conventional, and the command that opens one draft PR
for the `overnight/<time>` branch. `progress.md` holds each worker's notes,
and `.overnight/logs/<issue>.log` its full output. Greg playtests the branch. A parked issue keeps its label and a comment with the
verify output: fix the issue or the test, remove the label, and it rejoins the
next run.
