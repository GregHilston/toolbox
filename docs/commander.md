# Commander: watching orchestrators overnight

A commander is a Claude session that keeps one or more orchestrators working while Greg is
away: gridkeep's on foundation, loser-picks' on moria, or any repo run by `/orchestrate`.
The design for a cheaper commander (an XO script that wakes it only on a problem) is in
`.scratch/commander-script/` on dungeon. The first night's lessons and numbers are in
`~/Git/notes/llm/commander-lessons-2026-11-18.md`.

## The rule: every fix gets a root cause and a guard

Greg, 2026-11-19: each time the commander unsticks an orchestrator, it also finds out why
it got stuck, and makes that harder or impossible to happen again.

1. **Fix first.** Get the orchestrator working again: nudge, answer, or roll it by hand.
2. **Find the root cause,** not the symptom. Ask why until the answer is a tool, a doc or a
   setting you can change. "It was idle" is a symptom; "its wait depended on a notification
   that a Claude restart drops" is a cause. Check it against evidence (screen, logs, code)
   before writing it down.
3. **Add a guard,** the strongest one that's cheap enough:
   - a code fix with a test that fails first (best);
   - a ticket in the repo that owns the cause, at a priority that matches the cost of a
     stall, with the evidence in its body;
   - a line in the repo's orchestrator docs or the restart prompt (weakest: on 2026-11-18,
     a prompt rule against high load didn't hold).
4. **Record it** in the table below, and in the night's lessons file.

Toolbox changes still need Greg's OK, asked per change. While he sleeps, file them in
`.scratch/` and list them in the morning report.

## Working rules

- Reach hosts by Tailscale name (`moriats`, `foundationts`); from dungeon the plain aliases
  fail, and the Claude sandbox blocks ssh.
- Talk to an orchestrator with `hc send`, then `hc wait` and `hc read`. Read the screen back
  to prove the message landed.
- To answer a blocked pick: read the screen, move with `hc keys <t> down…`, then
  `hc send --force` for a typed answer.
- Put standing orders in the orchestrator's restart prompt too
  (`HC_TERMINAL_ID=<t> shift-arm --prompt …`), or its next roll forgets them.
- A load rule names a threshold, not a host. "Keep everything on moria" put 19 Godot runs
  there, at load 50, while foundation sat at load 4.
- Check a subagent's surprising claim before relaying it. "Luna gets no cache" was wrong.
- Greg asleep: no `AskUserQuestion`. Take the recommended option if it can be undone, follow
  the standing orders for money, and Pushover only what he must act on.

## Root causes found so far

| Date | Symptom | Root cause | Guard |
|---|---|---|---|
| 11-18 22:16 | loser-picks idle, "Needs input", only a train running | A Claude Code restart (likely an auto-update) dropped its background tasks, so the train's "done" notice never came | Waits read files, not notifications: gk #1647, lp #333. Shift sessions don't auto-update mid-shift: `.scratch/shift-no-autoupdate/` |
| 11-18 22:35 | Roll refused in an hc terminal | `orchestrator-roll`'s pre-roll check called `herdr agent get` | Fixed with a test: toolbox `6721d6a`, `e53fac7` |
| 11-18 22:30 | Restart prompt said "moria only" and listed nothing to build during trains | The prompt was hand-written for one night | New prompt; the shift brief carries the rule: gk #1645, lp #331 |
| 11-18 23:20 | gridkeep held builders until its train ended | No written rule that builders run during trains | The shift brief: gk #1645, lp #331 |
| 11-19 00:20 | moria at load 47, trains timing out | Unit runs hit the 600 s shim cap when a loaded gate gets one shard | lp #328, #329, #303 (spike lp #326) |
| 11-19 00:45 | Both orchestrators blocked on a money pick | Gateway cap $10/day below the $20 top-up; orchestrators block on picks while Greg sleeps | home-lab cap check (below); the brief says picks default to standing orders |
| 11-19 02:05 | loser-picks' tests on foundation during gridkeep's gate, load 38 | Nothing shares cores across repos | lp #303, gk #1582 (one pool for both) |
| 11-19 03:13 | loser-picks draining, waiting on a builder that had ended | The orchestrator trusted its belief that #328's builder was running; nothing checked | `orch_wait` reports dead jobs: gk #1647, lp #333 |
| 11-19 03:29 | gridkeep idle 40 min after its roll gave up | The roll worker waited on two frozen subagents, logged `FAILED` and told no one; its reaper needs `lsof`, which foundation lacks | `.scratch/roll-drain-failures/`; the watcher flags a `FAILED` roll log |
| 11-19 04:00 | moria at load 47–56; moving runs to foundation only raised foundation to 20 | Too much ran at once; where it ran didn't matter | A count the orchestrator controls: at most 2 builders or fix rounds plus 1 train |
| 11-19 05:05 | gridkeep's roll gave up again | The drain wait (20 min) is shorter than a healthy fix round | `.scratch/roll-drain-failures/`: keep waiting while output moves |
| 11-19 05:42 | load 43 once #303's pool landed and the cap was lifted | The pool books one core per verify, which starts several shards, and gate tests book none | lp #339; keep an interim cap until the real guard is measured working, not just landed |
| 11-19 06:30 | gridkeep ran a hand-built stack gate with no builders while P0 #1651 sat unstarted | The brief's "full gate only when builders are idle" read as "hold builders for a gate"; the no-waiting rule named only trains. Second time: the 23:20 brief line didn't hold | gridkeep `63b2f2e64` (a builder never waits for a gate), and gk #1673: the status call flags a gate with no builders and ready P0 work |
