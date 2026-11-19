---
name: herdr
description: Drive Herdr, the terminal multiplexer Greg runs agents in, in its TUI or its desktop app. Open terminals, run commands in them, start a named Claude, pi or Codex session beside you, send it prompts and read its answers. Use when Greg mentions Herdr, or wants a session he can watch or talk to himself. Not for behind-the-scenes research or one-shot reviews, which stay subagents or pi-ask. Requires HERDR_ENV=1 (TUI) or HC_TERMINAL_ID (desktop app).
license: MIT
---

# Herdr

Run these in your shell (the `terminal` tool in Hermes, Bash in Claude Code,
`bash` in pi). Greg runs Herdr two ways. Check which one you are in:

```bash
if [ -n "${HC_TERMINAL_ID:-}" ] && [ -z "${HERDR_PANE_ID:-}" ]; then echo desktop
elif [ "${HERDR_ENV:-}" = 1 ]; then echo tui
else echo neither; fi
```

If it prints `neither`, say you are not inside Herdr and stop. `desktop`
means the `hc` section below. `tui` means print the guide from the installed
binary with `herdr --skill` and follow it, so it always matches the installed
version.

Rules for both:

- **A peer session is for talking it over.** Start one when Greg wants a
  reviewer or second agent he can see and ask again. For one-shot delegated
  work, keep using your harness's own subagents or `pi-ask.py`: an
  interactive session has no spend cap, no turn cap and no structured result.
- **Never start Opus** unless Greg asks.
- **Ask a peer for a long answer as a file.** Tell it to write Markdown to a
  path, then read the file instead of scraping its screen.
- **Close only what you made.** Never touch another terminal, even an idle one.

## Desktop app (`hc`)

`hc <cmd> --help` documents each command. An address is `t7`, a name, or
`machine/t7`. In `hc run`, put flags such as `--json` before the command, or
they go to the command.

Start a named peer. `--name` takes 1-32 of `a-z 0-9 - _` and must be unique
among live terminals:

```bash
hc run --json --bg --name reviewer --cwd "$PWD" claude --model sonnet
hc run --json --bg --name helper --cwd "$PWD" pi --model cloud
```

The reply holds the `address`. The peer's parent is your own terminal by
default: it ends when your program ends, and `hc` types a note into your
terminal when its turn ends. Add `--outlive-parent` to keep it alive, or
`--no-parent --no-notify` for a peer that stands alone.

Send a prompt, wait for the turn to end, then read the screen:

```bash
hc send --wait reviewer "Review the diff on this branch. Write findings to /tmp/review.md."
hc read reviewer | tail -40
```

- `hc send` pastes the text and presses Enter. `--if idle` skips the send when
  the peer is busy.
- `hc get reviewer --json` shows `status.state`: `idle`, `working` or
  `blocked`. A blocked peer waits on a permission or trust prompt: read the
  screen, then answer with `hc keys reviewer enter`.
- `hc wait reviewer` blocks until it stops working. A wait checks in after
  `--timeout` seconds (default 180); call it again if the peer still works.
- To start with a task in one step, put it last:
  `hc run --json --bg --name x claude --model sonnet "the task"`.

Close only your own terminals, each command in its own call:

```bash
hc kill reviewer
hc rm reviewer
```

Never `kill`, `rm`, `send` or `keys` a terminal you did not start, orchestrators
and Greg's own sessions included. Never run `hc server stop`.

## TUI only

- **Pick the model after `--`,** for example
  `herdr agent start reviewer --kind claude --pane <id> -- --model sonnet`
  or `--kind pi --pane <id> -- --model cloud`.
- **Never run `herdr integration install` or `uninstall`.** It writes
  through the symlinks into the toolbox repo.
- **Never run bare `herdr`** (it attaches the TUI) or `herdr server stop`.
