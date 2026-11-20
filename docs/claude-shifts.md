# Claude shifts: ephemeral orchestrator sessions

An orchestrator session works in **shifts**. When its context reaches a threshold, it stops starting work, lands or parks what is in flight, writes what it learned into the repo's docs and tickets, then clears itself and starts again from one fixed restart message. Nothing compacts, and no handoff document is needed.

## Why

- **Context is the cost.** An Opus orchestrator re-reads its whole context on every turn. On 2026-11-13 one session reached 457k tokens and re-read 49M cached tokens in one evening; a session that rolls at 250k pays about half as much per turn.
- **Greg hates auto-compact.** A compaction summary keeps a lossy copy of everything. A shift keeps nothing in the chat; what matters is already on disk.
- **The tickets are the memory.** Our orchestrators already cut, update and close tickets and write lessons into the repo's docs as they go. So the state a new session needs is in GitHub and in `docs/orchestrating.md`, and the restart message never changes.
- **It stays interactive.** Headless `claude -p` workers use the 5-hour window 1.8 to 2.9 times faster (anthropics/claude-code#97074). A shift clears the same interactive Herdr pane, so Greg can watch it, type into it, and it bills like any session.
- Prior art: r/ClaudeCode "Can Claude Code automatically end its own session and start a fresh one?" (2026-11). Builders there used a context threshold, a handoff, `/clear` sent by a mod or tmux, and a hook that injects the next prompt. Claude Code itself has no model-callable `/clear` and no context-size hook (docs checked 2026-11-13), so this sits on a Stop hook and Herdr.

## How it works

1. **Arm.** The orchestrator runs `shift-arm --prompt '<restart message>'` from its own Bash tool. That writes `~/.cache/claude-shift/<pane>.json`, keyed by `$HERDR_PANE_ID` (TUI) or `hc:$HC_TERMINAL_ID` (desktop app), which survives `/clear` while the session id does not. Defaults: drain at 250,000 tokens, at most 8 rolls. Unarmed sessions are never touched.
2. **Measure.** `dot/claude/.claude/hooks/shift-drain.py` is a Stop hook. On every stop of an armed pane it reads the transcript's tail and takes the last assistant message's `usage` (input plus cache read plus cache creation) as the context size. It costs tens of milliseconds.
3. **Drain.** At the threshold it blocks the stop once, with instructions: start nothing new; land or park every in-flight ticket (background subagents die with `/clear`); write lessons into the repo docs and status onto the tickets; file a ticket for every bug, follow-up or unfinished piece the shift found, and split a blocked ticket's Greg-free build into its own ready ticket; then run `orchestrator-roll`. Only if, after that filing, every open ticket in the milestone needs Greg, send one Pushover listing them and stop instead (2026-11-14: a shift stopped while three spikes held agent-buildable work behind a manual step).
4. **Roll.** `orchestrator-roll` checks the cap and launches a detached worker. It exits 0 when the roll is queued, 1 when it refuses (with the reason), and 2 for bad arguments. The worker holds `/clear` until three things are true: a Stop newer than the roll, no live `background_tasks` or `session_crons` in that Stop, and an agent that has stayed idle for 3 seconds. That way `/clear` never kills a running subagent. Then it submits `/clear` with `herdr agent prompt` (`hc send` in the desktop app), waits, and submits the restart message.
   - **Counting:** the roll counts only once the restart prompt is delivered.
   - **Failure:** a Herdr error body, or 20 minutes of waiting, sends a Pushover and leaves the session alone. The next Stop drains again, and the cap bounds the retries.
   - **Reaper:** while `busy` stays above 0, the worker runs `bin/roll_reap.py` every minute and logs each kill. Claude Code's task list is invisible to it, so it works on processes: a `godot`, `gate_test.sh` or `verify.sh` older than 15 min (`ROLL_REAP_GRACE`) under a scratchpad or `worktrees/` dir, descended from `claude` or orphaned, dies with its process group. Any subagent transcript written in the last 2 min (`ROLL_AGENT_QUIET`) stops all reaping. `orchestrator-roll --reap --dry-run` lists first.
   - **Cancel:** `shift-arm --off` cancels a queued roll.
   - **Log:** `~/.cache/claude-shift/<hash>.log`. A roll takes about 14 seconds when nothing is running.
5. **Resume.** The fresh session reads the restart message, re-arms itself (the roll count is kept), reads `docs/orchestrating.md` and the milestone's tickets, and carries on.

## What a repo needs

- **Tickets that carry state.** A milestone label is the queue. `stage:building`, `stage:reviewing` and `stage:fixing` mark in-flight tickets, with a comment naming the branch, the worktree and any review findings not yet sent. `needs-greg` marks a ticket blocked on Greg's hands, taste or money, with one line saying what.
- **Lessons where the next shift reads them.** The repo's `docs/orchestrating.md`, its `CLAUDE.md`, and the orchestrate skill, as `~/.claude/CLAUDE.md` "Ending a chat" says.
- **A fixed restart message**, written in the repo's `docs/orchestrating.md`.

## Commands

```
shift-arm --prompt '<restart message>' [--threshold 250000] [--max-rolls 8] [--repo PATH]
shift-arm --status
shift-arm ... [--drain TEXT] [--log RUN_LOG]  # a commander's drain text and run log (docs/commander.md); both kept on re-arm
shift-arm --off            # disarm and reset the roll count
orchestrator-roll          # what the drain message tells the model to run
```

## How it was checked

- Opus built it on 2026-11-13. DeepSeek, Luna and Sonnet reviewed it independently, and their merged findings went into one fix round.
- `tests/test_claude_shift.py` has tests with stand-in `herdr`, `hc` and `pushover` scripts.
- The live run used a throwaway Haiku pane: two rolls, a third block refused by the cap, and a background job that held `/clear` for 45 s until it ended.

## Known limits

- `shift-arm` refuses to arm when the Stop hook can't run: the hook file is missing or not executable, or no `hooks.Stop` command in `settings.json` names it (`CLAUDE_CONFIG_DIR` moves the `~/.claude` it checks).
- `orchestrator-roll` refuses when `stops` is 0, meaning the Stop hook has never fired on this pane. Re-arming keeps `stops`, so the check means "never fired since the pane was first armed"; `--off` resets it.
- State files are locked (`fcntl`) and validated. A corrupt file is moved aside with one Pushover, and the pane counts as unarmed until re-armed.
- The worker holds the lock while it sends `/clear`, for up to 60 s, which stalls that pane's Stop hook for the same time.

- The hook may read the previous API call's usage, so a drain can start one turn late.
- Claude Code labels the drain message "Stop hook error"; that is how it shows any block reason.
- A pane stuck at a permission prompt or a question for 20 minutes after a roll gives up, with a Pushover.
- Text typed into the pane during a roll mixes into the `/clear`.
- Draining is the model's job. The hook announces it once per session.
