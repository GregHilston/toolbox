---
name: herdr
description: Drive Herdr, the terminal multiplexer Greg runs agents in. Open panes, run commands in them, start a named Claude, pi or Codex session beside you, send it prompts and read its answers. Use only when Greg mentions Herdr or asks for a pane, tab or another agent session he can see and talk to. Requires HERDR_ENV=1.
license: MIT
---

# Herdr

Run these in your shell (the `terminal` tool in Hermes, Bash in Claude Code,
`bash` in pi). First check you are inside a Herdr pane, then print the full
guide from the installed binary and follow it:

```bash
test "${HERDR_ENV:-}" = 1
herdr --skill
```

If the check fails, say you are not inside Herdr and stop. The guide comes
from the binary so that it always matches the installed version; don't work
from memory of an older one.

Greg's rules on top of the guide:

- **A peer session is for talking it over.** Start one (`herdr agent start`)
  when Greg wants a reviewer or second agent he can see and ask again. For
  one-shot delegated work, keep using your harness's own subagents or
  `pi-ask.py`: an interactive session has no spend cap, no turn cap and no
  structured result.
- **Pick the model after `--`,** for example
  `herdr agent start reviewer --kind claude --pane <id> -- --model sonnet`
  or `--kind pi --pane <id> -- --model cloud`. Never start Opus unless Greg asks.
- **Never run `herdr integration install` or `uninstall`.** It writes
  through the symlinks into the toolbox repo.
- **Close only the panes you made.** Never run bare `herdr` (it attaches the
  TUI) or `herdr server stop`.
- **Ask a peer for a long answer as a file.** Tell it to write Markdown to a
  path, then read the file instead of scraping its screen.
