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
3. **Add a guard in code, not in a prompt.** Greg, 2026-11-19: enforce a limit in code
   rather than by telling an orchestrator. In order of preference:
   - a code fix with a test that fails first;
   - a ticket in the repo that owns the cause for that fix, at a priority that matches the
     cost of a stall, with the evidence in its body. Hooks, settings, labels and checks in
     the status call all count as code;
   - a line in the orchestrator docs or the restart prompt, only as a stopgap until that
     ticket lands, never on its own. Prompt rules failed twice in one night: high load on
     2026-11-18, holding builders for a gate on 2026-11-19.
4. **Record it** in the table below, and in the night's lessons file.

A commander may edit and push this file without asking (Greg, 2026-11-19): root causes,
rules and lessons. Other toolbox changes still need Greg's OK, asked per change. While he
sleeps, file them in `.scratch/` and list them in the morning report.

## Working rules

- **Voice, for fun** (Greg, 2026-11-19): Battlestar Galactica ranks, used lightly. Greg is
  President Hilston, you are the Commander, the watcher script is your XO, each
  orchestrator is its repo's CAG, and builders are its Viper pilots; never at the cost of
  clarity. Give a CAG its line in the restart prompt too.
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
- Read a ticket's body before naming it as the vehicle for a plan. On 2026-11-19 "#327 is
  the two-host pool" was wrong, and the real ticket (#355) started an hour late.
- The watcher (`.scratch/commander-script/alerts.sh`, dungeon) exits on its first alert and
  after its 2-hour timeout: re-arm it every time it ends. It alerts on "Needs you
  (Commander)" and saves a `ps` snapshot on load over 32.
- `shift-start.md` re-runs `shift-arm`, which resets the roll count, so `max_rolls` never
  binds: a CAG that reads "roll 8/8" keeps rolling.
- A slot cap counts sessions, not cores: watch load, not the builder count.
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
| 11-19 07:57 | moria at load 59 with only 2 builders and 1 train | `gate_test.sh` runs `GATE_TEST_JOBS` plants at once, 16 by default, and heavy plants each start a nested `./verify.sh` with its own shards; the cap counted sessions, not cores | lp #339 (gate tests book their real cores); meanwhile `GATE_TEST_JOBS=4` in the restart prompt |
| 11-19 10:50 | moria's load rose and loser-picks' third builder slot closed | #345's builder exited and left its load-test burners (`yes`) running: they had left the builder's process group, so `tools/pi_build.sh`'s kill on exit missed them | lp #350: a builder's exit stops every run its worktree still has, with a test |
| 11-19 12:00 | loser-picks waited 45 min on a question to the commander | The watcher checked only `blocked`, and a question on screen leaves the terminal `working`; the orchestrator asked about a reopen rule it could have applied itself | `alerts.sh` alerts on "Needs you (Commander)"; the orchestrator reopens the slot itself after 15 min under load 24 |
| 11-19 14:02 | moria offline 6 min, with loser-picks' orchestrator and builders on it | Its only monitor was switched off with the lid closed, so macOS clamshell-slept on AC; Vorssaint and caffeinate block only idle sleep | toolbox `d441983`: a root daemon sets `disablesleep 1` on AC and 0 on battery |
| 11-19 16:23 | train-r1700 failed `test_gate_pool.sh` on foundation at every prefix holding lp #339 for 2.5 h; the CAG blamed Linux or load | The outer `gate_test.sh` exports `GATE_TEST_PLANT_SHARDS` (3 on 16 cores) and the untouched copy's nested test inherited it; the CAG's moria repro had no outer gate, so it passed | lp `c9e542bf`: `gate()` strips the variable from a plant's verify, with a test that fails with it set. Reproduce a gate-only failure under the gate's own env before blaming the host |
| 11-19 20:44 | train-s1119 failed: every plant copy in the gate test showed a second `test_gate_pool.sh` error; nothing landed 18:46–20:44 | The same leak again: the nested test inherited the plant's `VERIFY_SHARDS=1`. The commander's 19:00 repro checked only the untouched copy, so the first guard named one variable | lp `6d995626` (that unset); lp #368 strips the outer shard and pool variables from every gate test, so a guard covers the class, not the name |
