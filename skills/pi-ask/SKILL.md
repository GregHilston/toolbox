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
pi-ask.py --session NAME --dir /abs/dir "task"           # first turn
pi-ask.py --session NAME "follow-up"                     # same NAME: same conversation and dir
pi-ask.py --session NAME --dir /abs/dir @/abs/prompt.md  # a long prompt, from a file
pi-ask.py --session NAME --max-cost 1.00 "big task"      # raise the spend cap (default $0.50)
```

Don't call `pi -p` yourself. With a stdin left open pi hangs before its first
model call and prints nothing, and in plain text mode a timeout loses whatever it
did; `pi-ask.py` handles both.

- **Name each task,** such as `review-pr-42`. Ask again with the same name to
  follow up: the worker keeps its context and its warm cache, so a follow-up
  costs a fraction of a cent. Push back on its answers this way.
- **The first turn fixes the dir.** A follow-up runs there without `--dir`, and
  a different `--dir` is refused (exit 2): pi keys sessions by directory, so
  another one would start a new conversation. Use a new name for a new dir.
- **In Claude Code, run it with `run_in_background: true`.** It prints a start
  line, any alert lines (`✗`, `!`, `⚠`), then the answer, its cost and the
  follow-up command. The step-by-step narration goes to
  `~/.cache/pi-ask/NAME.log`; read it only if the answer puzzles you. You are
  notified when it exits; read the output then. Don't poll, and don't wrap it in
  `timeout`.
- **Write a long prompt to a file in one call,** then pass `@file` in the next.
  Put `--` before a prompt that starts with `-`.
- **Exit codes:** 0 answered; 1 the turn failed (the error prints after the
  answer); 2 bad arguments, or started from inside a pi worker; 3 silent for
  `--idle` seconds (default 300) and killed; 4 stopped past `--max-cost`
  (default $0.50) or `--max-turns` (default 100); 5 that session is already
  running, so wait for it. 129, 130 and 143 mean it was interrupted. After 3
  or 4, ask again with the same name to carry on.
- **It runs on the gateway's `cloud` model** (DeepSeek Flash), capped at $4 a
  day. The answer header gives two figures: the cost at DeepSeek's prices, which
  `--max-cost` uses, and the larger one the gateway counts against that cap,
  priced from `models.json`. Report both.
- **What the worker can touch.** It reads anything under `~/Git`; copy in
  anything else first. Its `edit` tool is refused outside `--dir`, but inside it
  can change and discard files (`git checkout -- .`, `sed -i`), and shell
  commands are not path-checked anywhere. It can't commit, push, pull or delete
  recursively. Point `--dir` at a clean checkout or worktree, never at work in
  progress. Toolbox scripts such as `reddit-search.py` are on its `PATH`;
  `pi-ask.py` itself refuses to run there.
- **"No project session found with id …" on a follow-up is a problem:** pi lost
  the conversation and started afresh. Say so rather than trusting the answer's
  memory of earlier turns. pi-ask hides it on a first turn, where it is normal.
