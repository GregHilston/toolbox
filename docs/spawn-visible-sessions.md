# Spawning a Claude session Greg can see from his phone

How a commander or orchestrator starts a Claude session that shows in both the Claude Android
app (Code) and the Herdr Android app. First used 2026-11-21 on dungeon, when one session
started five Opus "burn" sessions; that run's note is `~/Git/notes/llm/spawn-visible-claude-sessions-with-hc.md`.

## When to spawn one, and when not

A visible session is for work Greg will watch or talk to: a new orchestrator (CAG), or a
long job he wants to check from his phone. Work that only hands back a result runs as an
Agent-tool subagent or `pi-ask` instead (`~/.claude/CLAUDE.md`, "A Herdr pane is for work I'll
watch or talk to"). Never spawn one just to make work visible.

## Why `hc run` and not a Herdr pane

The phone and desktop apps talk only to herdr-core (`hc`), never to the TUI's server
(`docs/phone-control.md`). A session started with `hc run` lives in herdr-core, so the apps see
it; a TUI pane never shows. The parent needs only `hc` on `$PATH` and a running core.

## The command

```bash
hc run --json --bg --no-parent --no-notify --name <name> --cwd <dir> \
  claude --model <model> --remote-control <name> --dangerously-skip-permissions "<the whole task as one prompt>"
```

- `--remote-control <name>`, the same name as `--name`, is what puts it in the Claude app's
  Code list. Without it the session prints `/rc connecting…` and one batch never reached the
  Claude app, though it showed in the Herdr app (2026-11-21).

- `--bg` returns at once, so one Bash call can start several.
- `--no-parent --no-notify`: the child outlives its parent and types nothing into it. A
  commander needs this: its pane already takes `XO:` alerts, and a parent's restart would
  otherwise end the child. The cost is no wake-up on exit, so watch it (below).
- `--name`: 1-32 of `a-z 0-9 - _`, unique among live terminals; the phone apps show it.
- `--cwd` picks which project's `CLAUDE.md` it loads.
- `--on moriats` or `--on foundationts` starts it on another machine; its address becomes
  `moriats/t7`. Use the Tailscale names (`hc machine ls`).
- `--model` is required. Pick it by `docs/claude-model-picking.md`: Opus only when Greg asked.
- `--dangerously-skip-permissions` for anything nobody watches: `--permission-mode acceptEdits`
  still prompted on every Bash call, and the five burn sessions sat blocked until restarted.
  Pair it with hard limits in the prompt: branches only, no merges, delete nothing, no AI
  attribution, builds on another host.
- Interactive, not `claude -p`: headless runs drain the 5-hour window 1.8-2.9x faster.

Check it started right: `hc read <name> | grep -o 'Opus[^|]*\|Sonnet[^|]*\|bypass permissions\|/remote-control is active'`.
All three must show; a banner stuck on `/rc connecting…` won't reach the Claude app.

## The task prompt

- The task goes last, as one quoted string. Build a shared preamble in a shell variable and
  append each child's item.
- Say it runs unattended: never ask Greg, take the safe default, note it in the report.
- Ask for a result file (`llm/<run>-report-<item>.md`) rather than scraping the screen.
- An orchestrator gets its CAG line and standing orders here, then arms its own shift with
  `shift-arm --prompt` so a roll keeps them (`docs/commander.md`, "Put standing orders in the
  orchestrator's restart prompt too").

## Watching and stopping

```bash
hc ls                              # address, name, status, turn
hc read <name> | tail -30          # the screen
hc send --if idle <name> "..."     # message it only when idle
hc wait <name>                     # until its turn ends (checks in every 180 s)
hc kill <name>                     # only one you started
```

- `blocked` means it waits on a prompt: read the screen.
- A slash command sent with `hc send` arrives as plain text; type it with `hc keys`
  (`docs/commander.md`, working rules).
- Run each `hc kill` and `hc rm` in its own Bash call.
- A child with no parent wakes nobody. Give a spawned orchestrator an XO
  (`control-loop.sh --name <repo> --wake hc:<commander>`), and set an `xo-due` timer to read a
  one-off child's report.
- Never send to, kill or type keys into a session you did not start unless Greg says so, and
  don't say a message reached it until its screen shows it.
