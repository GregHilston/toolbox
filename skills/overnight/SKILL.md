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
overnight-loop.py --harness claude                  # Claude workers, auto permission mode
overnight-loop.py --harness claude --yolo           # only inside a container or VM
overnight-loop.py --harness pi --model deepseek/deepseek-v4-flash
overnight-loop.py --help                            # caps: --hours, --max-issues, --max-fails, --max-cost
```

Why a script and not you: an orchestrator that is itself a model session fills
its context over a night and compacts. The script holds no context, starts every
worker clean, and trusts `./verify.sh`, never a worker saying it is done.

## Before starting

Check these with Greg, then start it, and stop there:

1. **The repo passes agent-ready.** The script refuses to start without an
   executable `./verify.sh` that passes, or with a dirty tree.
2. **The queue.** Open issues with the label (default `ready-for-agent`; pass
   `--label prep:ready` after `/prep`). Each needs a checkable `Done when`.
3. **The caps.** Defaults: 8 hours, 20 issues, 3 parks in a row, 90 minutes per
   issue, and for Claude $10 per issue and $60 a night.
4. **The sandbox.** pi asks no permission for anything, and `--yolo` turns
   Claude's off. Run either inside a container or VM that mounts only this repo.
5. **Detach it.** Run it in `tmux new -d -s overnight '…'`, not as a harness
   background task, which dies with the session.

`touch .overnight/STOP` ends the run after the current issue.

## In the morning

The script prints which issues it finished and which it parked, and the command
that opens one draft PR for the `overnight/<time>` branch. `progress.md` holds
each worker's notes, and `.overnight/logs/<issue>.log` its full output. Greg
playtests the branch. A parked issue keeps its label and a comment with the
verify output: fix the issue or the test, remove the label, and it rejoins the
next run.
