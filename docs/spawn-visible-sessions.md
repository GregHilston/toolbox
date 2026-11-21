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
hc run --json --bg --outlive-parent --name <name> --cwd <dir> \
  --label project=<repo> --label role=<commander|cag|intake> \
  claude --model <model> --remote-control <name> --dangerously-skip-permissions "<the whole task as one prompt>"
```

- `--remote-control <name>`, the same name as `--name`, is what puts it in the Claude app's
  Code list. Without it the session prints `/rc connecting…` and one batch never reached the
  Claude app, though it showed in the Herdr app (2026-11-21).

- `--label project=<repo> --label role=<commander|cag|intake>` is what names the session
  `project/role` on the dradis board; the commander's project is `fleet`. Leave both off a
  child that is none of the three. Label a running one with `session-label <t> <role>`.
- `--bg` returns at once, so one Bash call can start several.
- `--outlive-parent`: the spawning terminal stays its parent, so `hc` types a note into it
  when the child's turn ends, but a spawner's roll or restart no longer ends the child.
  `--no-parent --no-notify` is one-way: nothing wakes the spawner, so use it only for a child
  nobody needs to hear from.
- `--name`: 1-32 of `a-z 0-9 - _`, unique among live terminals; the phone apps show it.
- `--cwd` picks which project's `CLAUDE.md` it loads.
- `--on` starts it on another machine: see "Other machines".
- `--model` is required. Pick it by `docs/claude-model-picking.md`: Opus only when Greg asked.
- `--dangerously-skip-permissions` for anything nobody watches: `--permission-mode acceptEdits`
  still prompted on every Bash call, and the five burn sessions sat blocked until restarted.
  Pair it with hard limits in the prompt: branches only, no merges, delete nothing, no AI
  attribution, builds on another host.
- The bypass flag does not skip every prompt: Claude Code still asks "can't be sure it read
  this command … dangerous removal" for odd shell, such as a long heredoc over `ssh`, and the
  child sits `blocked`. Greg answers it in the phone app; a parent in auto mode may be refused
  when it tries `hc keys <name> enter`.
- Interactive, not `claude -p`: headless runs drain the 5-hour window 1.8-2.9x faster.

Check it started right: `hc read <name> | grep -o 'Opus[^|]*\|Sonnet[^|]*\|bypass permissions\|/remote-control is active'`.
All three must show; a banner stuck on `/rc connecting…` won't reach the Claude app.

## Other machines

`--on moriats` or `--on foundationts` (Tailscale names, from `hc machine ls`) starts the child
there from any machine, and it shows in both phone apps like a local one; both hosts showed
`/remote-control is active` on 2026-11-21. Its address becomes `moriats/t7`.

- **Always pass `--cwd`** with a folder already trusted on that host. Without it the child
  starts in `$HOME`, which Claude does not trust, and stops at "Yes, I trust this folder".
- Foundation is WSL with an older `claude`; check the banner for the flags you rely on.
- Address and kill a remote child by address (`hc kill foundationts/t8`), not by name: a name
  lookup from another machine said "not found" and left the name held.
- Moria's Claude login expires about every 3 days (`/login` renews it), and an expired login
  stops Remote Control. Check each host's banner after spawning.
- Citadel has no `hc` and takes no inbound SSH: never spawn there.

## Two-way messaging

Every spawned session knows how to reach its spawner and its siblings. A child can't guess
either, so the prompt names them:

```
You can message other Herdr sessions: `hc ls` lists them (address, name, status);
`hc send --if idle <name-or-address> "text"` messages one; `hc read <name>` shows its screen.
Your spawner is <NAME/ADDRESS>; your siblings are <LIST>. Tell your spawner in one line with
`hc send` when you finish or need a decision, and write the detail to a file.
```

- **The spawner needs an `hc` address.** A session run from a plain terminal outside Herdr has
  none, so its children can't reach it (the 2026-11-21 burn spawner was one). Start a spawner
  under `hc` or the Herdr desktop app.
- Remote siblings go by address: `hc send foundationts/t7 "..."`.
- Send only to sessions named in your prompt; never `keys`, `kill` or `rm` another session's
  terminal, and never answer its permission prompt: auto mode refuses, and Greg answers from
  the phone.

## The task prompt

- The task goes last, as one quoted string. Build a shared preamble in a shell variable and
  append each child's item.
- Say it runs unattended: never ask Greg, take the safe default, note it in the report.
- Tell it to keep shell simple: no long heredocs over `ssh`; write files with the Write tool and
  copy them across. That avoids the prompt the bypass flag can't skip.
- Name its spawner and siblings, with the messaging block above.
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
- A child's one-line `hc send` can vanish into a working spawner (`docs/commander.md`), so
  still give a spawned orchestrator an XO (`control-loop.sh --name <repo> --wake
  hc:<commander>`), and set an `xo-due` timer to read a one-off child's report.
- Never send to, kill or type keys into a session you did not start unless Greg says so, and
  don't say a message reached it until its screen shows it.
