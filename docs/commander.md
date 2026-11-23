# Commander: watching orchestrators overnight

How the whole fleet fits together, and why: `docs/fleet.md`.

A commander is a Claude session that keeps one or more orchestrators working while Greg is
away: gridkeep's on foundation, loser-picks' on moria, or any repo run by `/orchestrate`.
Its XO, a control loop that wakes it only on a problem, is `bin/control-loop.sh`. The first night's lessons and numbers are in
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
rules and lessons. Since 2026-11-20 a commander may also merge and push its own toolbox
changes without asking (Greg: "approved to merge, not just this but all things"). A bulk
GitHub read follows `docs/github-api.md`: the API quota is for development. Other toolbox changes still need Greg's OK, asked per change. While he
sleeps, file them in `.scratch/` and list them in the morning report.

## Working rules

- **Voice, for fun** (Greg, 2026-11-19): Battlestar Galactica ranks, used lightly. Greg is
  President Hilston, you are the Commander, the watcher script is your XO, each
  orchestrator is its repo's CAG, and builders are its Viper pilots; never at the cost of
  clarity. Give a CAG its line in the restart prompt too.
- **No-DeepSeek switch:** `~/.config/fleet/no-deepseek` (its text is the reason) makes `pi-ask.py`,
  `overnight-loop.py` and `pi-rpc.py` exit 76 on a DeepSeek model, and the XO alerts hourly when
  DeepSeek requests rose in 15 min (`bin/xo-deepseek.py`). Create it on every host for a Claude-only order.
- Reach hosts by Tailscale name (`moriats`, `foundationts`); from dungeon the plain aliases
  fail, and the Claude sandbox blocks ssh.
- Talk to an orchestrator with `hc send`, then `hc wait` and `hc read`. Read the screen back
  to prove the message landed. A send to a working terminal can vanish (2026-11-19 20:55):
  grep the screen for it and resend. Once lp #426 and #428 land, read the Chief's events before
  any screen and message over the socket instead (`docs/fleet.md`, "Why it is built this way").
- The XO is `bin/control-loop.sh` (env `XO_HOST`, `XO_TERM`, `XO_REPO`; loser-picks on moria
  by default). It runs as its own detached process, not a Claude background task, and types
  `XO: ...` into the commander's pane: see "Commander shifts". It alerts once per event, repeating after 1, 2, 4, then every 8 h while it lasts,
  on a blocked or missing CAG, a CAG idle over 20 min, a ticket approved but unlanded 30 min, free slots beside a ready P0 for 20 min (`bin/xo-work.py`), a question to the Commander, lost tasks, a failed roll, load over
  32, 90 min with nothing landed, a GitHub quota under 500, and a red main open 20 min. Every 10 min it also fast-forwards `~/Git/toolbox` on moriats, foundationts and the local host, and alerts when one can't (`bin/xo-toolbox.py`). Tickets to
  watch go in `~/.cache/control-loop/<name>/closes`, one number a line.
- To answer a blocked pick: read the screen, move with `hc keys <t> down…`, then
  `hc send --force` for a typed answer.
- `hc send` wraps its text in an `<hc from=…>` tag, so a slash command (`/clear`, `/model`) arrives
  as a plain message and never runs (2026-11-21). Type it as raw keys instead:
  `hc keys <t> / m o d e l space o p u s enter`, then read the screen and confirm any "Switch
  model?" dialog with `hc keys <t> enter`. `/clear` before `/model` skips that dialog. Typing into
  a pane only works while it is idle, so wait for `idle` or `done` first. Greg's `!` commands from
  his phone fail the same way: they arrive as text.
  A short slash command also runs when sent untagged: `env -u HC_TERMINAL_ID hc send <t> '/goal …'`
  (2026-11-22). Keep it short: a 900-char one arrived as pasted text, while 360 chars ran.
- To start an orchestrator or a long job Greg can see from his phone, use `hc run` with
  `claude --remote-control <name>`, not a Herdr pane, on any host but citadel (`--on`, always
  with `--cwd`): `docs/spawn-visible-sessions.md`. Use `--outlive-parent`, not `--no-parent
  --no-notify`, and name the spawner's address and the siblings in each child's prompt so it
  can `hc send` them. Add `--label project=<repo> --label role=<cag|intake>` to an
  orchestrator (`--label project=fleet --label role=commander` for a commander), so the dradis
  board shows `gridkeep/cag` and not `t17`. `session-label <t> <role>` labels one already running.
- Put standing orders in the orchestrator's restart prompt too
  (`HC_TERMINAL_ID=<t> shift-arm --prompt …`), or its next roll forgets them.
- A load rule names a threshold, not a host. "Keep everything on moria" put 19 Godot runs
  there, at load 50, while foundation sat at load 4.
- Check a subagent's surprising claim before relaying it. "Luna gets no cache" was wrong.
- Read a ticket's body before naming it as the vehicle for a plan. On 2026-11-19 "#327 is
  the two-host pool" was wrong, and the real ticket (#355) started an hour late.
- Re-running `shift-arm` keeps the roll count, threshold, max rolls, `--drain` and `--log`, so
  `max_rolls` binds across restarts; only `shift-arm --off` resets them. It replaces the prompt,
  so a standing order lives in the repo's `docs/shift-start.md`, not only in the prompt.
- A slot cap counts sessions, not cores: watch load, not the builder count.
- Greg asleep: no `AskUserQuestion`. Take the recommended option if it can be undone, follow
  the standing orders for money, and Pushover only what he must act on.

## Commander shifts

A commander rolls like an orchestrator, but its orders live in a run log, not in the repo's
tickets. Arm it from its own pane (Opus):

```
shift-arm --threshold 250000 --max-rolls 50 --log <run log> \
  --drain 'Rewrite the ## Current block of your run log: orders with expiries, watch list, incidents, questions, running subagents.' \
  --prompt 'Fresh shift. Read <run log>: its ## Current block and the last few ## Journal entries. Restart the control loop if its heartbeat is stale, then carry on.'
```

- **Run log.** A markdown file in a repo. `## Current` is rewritten at each roll: orders in
  force (each with an expiry), watch list, open incidents, open questions, running subagents.
  `## Journal` is append-only and dated, across dates. A restart reads Current and the last
  few Journal entries.
- **Orders are recorded in code.** The `log-order.py` UserPromptSubmit hook appends every
  prompt the commander receives to the log as `### <date time> Greg` (or `XO` when it starts
  with `XO:`).
- **`commander-roll`** is what the drain message tells a logged pane to run, in place of `orchestrator-roll`. It refuses
  unless `## Current` changed since the last roll, commits and pushes only the log (a push
  failure is printed, the roll goes on), then runs `orchestrator-roll`. It does not stop
  working subagents; the roll waits for them.
- **Control loop.** Start it detached, once per commander (a second one on the same name
  refuses and prints the holder's pid):

  ```
  nohup control-loop.sh --wake hc:<terminal> > ~/.cache/control-loop/xo.out 2>&1 &
  ```

  `--wake herdr:<pane>` for a Herdr pane. It waits for the target to go idle and for a queued
  roll to finish, types the alerts, and retypes once if the text is not on screen. `--once`
  prints one pass of alerts and wakes nobody. Its state is `~/.cache/control-loop/<name>/`
  (nothing-landed clock, alert keys, `heartbeat`).

## Check that a change did its job

Every slip on 2026-11-19/20 was a change that landed and did something other than the plan
assumed, found hours later: the two-host pool sent 5 of 806 launches far (4 h); the copied
landing model held every landing on a red canary (2 h); a fix covered one copy kind and a
second leak failed the next train; a delegated script spent the shared GitHub quota.

- **Within an hour of a plan's change landing, measure the number it was for** (the ledger's
  host share, landings per hour, time per stage with `ticket-lanes.py`) and write it in the
  night's lessons. If no number moved, find out why before anything else. Where a script
  can see the failure, add it to the XO.
- **When one repo copies another's process, diff the behaviour, not the summary.** The
  ticket names the source's files and functions, and lists each behaviour the copy must
  match, including what happens on failure. Before it lands, read the source's code for
  every failure path and check the copy does the same, or names the difference as a
  decision. `land_branch.sh` held on red; gridkeep's `pilot.sh` never does.
- **A fix covers the class, not the instance.** Reproduce in every variant the failure can
  take (each copy kind, each host, each env), and when a second instance turns up, guard
  the class in code (lp #368).
- **A delegated task that touches a shared resource is told the budget**: the GitHub quota
  (`docs/github-api.md`), cores and load, Claude and DeepSeek spend. The brief says how much
  it may use and what to check before a bulk call.

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
| 11-19 23:27 | moria at load 45, foundation at 0 | #371's builder (a Claude subagent) ran a script of 20 `python3 -c 'while True: pass'` burners three times to test load handling; `builder_cap.py` reads `CAP_LOAD` for a faked load, but nothing makes a builder use it | lp #373 (P0): the `builder_cap.py` Bash hook refuses CPU burners and points at `CAP_LOAD`. The commander can't kill processes (auto mode refuses); the CAG can |
| 11-20 00:16 | tools train failed with culprit=-; no ticket closed in the trial's first 2 h | `test_orch_status.sh` wrote its sample train log under a fixed `2026-11-19/train-000200`; after 24 h `ago()` prints days and the `[smh]` pattern fails, so main itself failed. Separately the CAG held three free slots during the train | lp #375 (P0): sample logs dated from the clock. A test fixture never carries a calendar date. Checked: builders run during trains (lp #331), re-said to the CAG |
| 11-20 02:18 | foundation at load 0 four hours into the two-host trial | `hostpool.py` keeps every whole verify on moria (it writes counts into that tree), and builders' runs are almost all whole verifies: 5 of 806 launches went far | lp #378 (P0). Check a plan's vehicle against the ledger within its first hour, not only its ticket body |
| 11-20 04:20 | GitHub API quota 0 of 5000 on Greg's account until 05:03, so orchestrator `gh` calls fail | The commander's subagent tested `ticket-lanes.py` (about 400 timeline calls a run) several times in an hour; nothing counted the quota the orchestrators share | `ticket-lanes` `7227530`: refuses a run that would leave under 1,500, with a test. The XO alerts once per window under 500. A delegated script that calls an API gets told the shared quota |
| 11-20 07:30 | loser-picks landed one commit in 80 min after adopting gridkeep's landing model | Its canary holds every landing while main is red (`b9c79172`); gridkeep's never does: it bisects, files `fix(train)`, puts it first and keeps landing. No green sha was recorded, so nothing bisected | lp #393 (no hold), #394 (green sha, bisect), #395 (light check runs the count checks art and data touch). When a repo copies the other's process, diff the copy against the source's code, not its summary |
| 11-20 13:13 | loser-picks CAG idle 82 min while three pi lanes finished | Lanes started with `nohup … &` wake nobody on exit; loser-picks has no Chief yet (lp #397, P0, unstarted), and the XO never checked for an idle CAG | `70fed5b`: the XO alerts on a CAG idle over 20 min, with a test. #397 ordered first. Watchers watch each other: `.scratch/fleet-watchers/` |
| 11-21 03:20 | gridkeep roll FAILED, busy 1 after 20 min; CAG idle | The roll reaper never ran on foundation: it called `lsof` (missing there) and treated only pid 1 as init, while Linux orphans go to the `systemd --user` subreaper. 11-19 03:29 named the `lsof` gap, and nothing fixed it | `roll_reap.py` reads `/proc/<pid>/cwd` and counts a systemd parent as orphaned; its 7 tests failed 4 on foundation, now pass there and on moria |
| 11-21 08:30 | DeepSeek spend under a Claude-only order | The order lived in prompts; gk's `review_lane.sh` defaults to pi-ask and nothing checked spend | The switch file plus the XO alert (`bin/xo-deepseek.py`) |
| 11-21 09:05 | gridkeep roll FAILED again, busy 3 for 20 min; CAG idle | foundation's toolbox checkout was 54 commits behind, so the 03:20 `/proc` reaper fix never ran there (it was tested in a scratch copy); a stuck #1745 builder subagent held the count | Fast-forwarded foundation; proposal `.scratch/toolbox-stale-hosts/`: the XO alerts when a host's toolbox is behind origin/main. A fix tested on a host is deployed to that host's live checkout |
| 11-21 11:01 | loser-picks roll FAILED after the 20-min drain (gridkeep the same at 11:50, two background shells), CAG drained an hour with only #468 building | The drained CAG kept its own 50-min `orch_wait` on a detached canary (survives /clear) and re-drains each stop answered "the roll waits on it" | Commander told it to stop the wait and roll (11:59). Guard to build: a re-drain after a FAILED roll names the live tasks and says a wait on a detached job is not live work |
| 11-21 12:35 | lp landing #314 waited 57 min in its gate at load under 3 | The canary bisect ran `gate_test.sh` and held `/tmp/lp-godot-gate.lock` ahead of the landing | Canary stopped; lp P0 ticket: a bisect never holds the gate lock ahead of a landing. Check load and the child tree before calling a landing busy |
| 11-21 14:06 | lp first two stacks red, nothing landed 13:19-15:00 | Stacked branches each add a docs entry and nobody regenerated the views; an untracked Godot `.uid` held #468 and #478 as dirty | lp #478 (regenerate on the stack, drop branches named by errors) lands before the next stack; track the `.uid`. Land a fix for a failure class before the next stack |
| 11-21 22:45 | lp CAG ran 4 builders under a cap-10 order; dradis armed 250k/8 under a 200k/20 order | A CAG re-arms itself from its shift-start doc: the new prompt replaced the one carrying the order, and a re-arm without flags reset threshold and max rolls to defaults | `shift-arm` keeps threshold and max rolls unless given, with a test; orders go in each repo's `docs/shift-start.md` |
| 11-23 02:00 | lp roll FAILED: no idle stop in 20 min, CAG past its limit | The Commander set a `/goal` on the CAG; an unmet goal starts a new turn at once, so the drain never saw an idle stop. The CAG's own wait shell (the 11-21 11:01 class) added to it | `/goal clear`, plain restart prompt; `docs/claude-shifts.md` "No `/goal` on a shift session". Check a new Claude Code feature against the roll before using it on a CAG |
| 11-23 03:08 | No XO wake while lp landed nothing 01:38-04:30; Greg found it | The XO's new backoff (1c46944) kept the "nothing landed" count from the 23:06 episode, so the next stall waited 4 h. It reset only after twice the wait, never when the condition cleared | `control-loop.sh`: a pass without an alert resets its count (1 h floor kept), with a test that fails on the old code |
