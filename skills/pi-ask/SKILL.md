---
name: pi-ask
description: Hand a task to a cheap DeepSeek pi worker and talk it over across several turns, for research, a PR review or a second opinion. Use when Greg asks to delegate to pi or DeepSeek, or for bulk reading not worth Claude tokens. Not for code changes, which go through /orchestrate-pi or overnight-loop.py.
license: MIT
---

# pi-ask

One command, already on `PATH`. Run it in your shell (the `terminal` tool in
Hermes, Bash in Claude Code, `bash` in pi) exactly as shown: no `python3` in front
and no directory.

```bash
pi-ask.py --session NAME --dir /abs/dir "task"             # first turn
pi-ask.py --session NAME --dir /abs/dir "follow-up"        # same NAME and dir: same conversation
pi-ask.py --session NAME --dir /abs/dir @/abs/prompt.md    # a long prompt, from a file
```

Don't call `pi -p` yourself. With a stdin left open pi hangs before its first
model call and prints nothing, and in plain text mode a timeout loses whatever it
did; `pi-ask.py` handles both.

- **Name each task,** such as `review-pr-42`. Ask again with the same name and
  `--dir` to follow up: the worker keeps its context and its warm cache, so a
  follow-up costs a fraction of a cent. Push back on its answers this way.
- **In Claude Code, run it with `run_in_background: true`.** It prints one line per
  worker step, then the answer, its cost and the follow-up command. You are
  notified when it exits; read the output then. Don't poll, and don't wrap it in
  `timeout`: it kills a worker silent for `--idle` seconds (default 300) and exits 3.
- **Write a long prompt to a file in one call,** then pass `@file` in the next.
  Put `--` before a prompt that starts with `-`.
- **Exit 3 means it stalled.** The log path printed at the end holds everything it
  did; ask again with the same name to carry on.
- **It runs on the gateway's `cloud` model** (DeepSeek Flash), capped at $4 a day.
  Report the cost in the answer header; the narrator's "done" line uses pi's
  stale prices.
- **The worker can't commit, push or delete recursively, but it can still edit
  and discard files** (`git checkout -- .`, `sed -i`). Point `--dir` at a clean
  checkout or worktree, never at work in progress. Toolbox scripts such as
  `reddit-search.py` are on its `PATH`.
- **Two warnings are normal:** "No project session found with id …" on a first
  turn, and "No models match pattern deepseek/*" on every turn.
