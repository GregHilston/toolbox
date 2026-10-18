---
name: swarm
description: Orchestrate a repo's backlog autonomously. Ask Greg a few questions up front, then run parallel overnight-loop lanes, review and land each branch with subagents in worktrees, get DeepSeek second opinions, and turn audits and playtest findings into tickets until only manual work is left. Use for /swarm, or when Greg asks to work the tickets while he is away.
disable-model-invocation: true
argument-hint: "[goal for this session]"
license: MIT
---

# Swarm

You are the orchestrator. You write tickets, start lanes, review, land and plan the next round. Subagents and loops write the code. Your context is the scarce thing: delegate file dumps, keep conclusions.

## 1. Interview, then go

Read the repo's `CLAUDE.md`, its design and ADR docs, its glossary, `docs/orchestrating.md` if present, and the open issues. Then ask Greg **one** `AskUserQuestion` round (at most 4 questions, a recommended option first) covering only what you cannot decide alone, typically:

- the goal for this session and what is out of scope
- whether DeepSeek is off-peak now and the real-money cap (`--budget`); Claude runs on the Max subscription, so its loop figures are list-price estimates
- whether you may land on `main` and push without asking (default yes, after a green gate and a review)
- anything only he can judge that is blocking (feel, taste, hardware)

Tickets labelled `next-session` were queued by the last session for you: start there, relabelling each into a lane.

After that, work autonomously. Don't ask again; make the call, note it, and put anything needing his hands, ears or judgement in a `manual` + `attended` ticket that no loop picks up.

## 2. Tickets

- One GitHub issue per change: _What to build_ (why, with file paths and glossary words) and _Done when_ (checkboxes a test, `./verify.sh` or a capture can check). Loop workers have no display, so their _Done when_ must be test-checkable; capture checks go to a subagent.
- Verify every finding you ticket: grep the code yourself before filing. Audits and reviewers are sometimes wrong.
- Domain changes (a new screen, vehicle, rule) go into the design doc and glossary first, in Greg's words, so tickets can use them.

## 3. Lanes

A lane is one `overnight-loop.py` in its own clone working one label, so lanes never pick the same issue. Put tickets that touch the same files in the same lane, in order; spread the rest.

```bash
lane.py start <lane> --label <label> -- --harness claude --model sonnet --reviewer claude --reviewer-model sonnet
lane.py start <lane> --label <label> -- --harness pi --reviewer pi --budget 2 --off-peak
lane.py status
lane.py fetch <lane>           # finished branch → worktree, rebased onto main
lane.py land <worktree>        # gate, fast-forward main, raise the baseline, push, close issues
lane.py stop <lane>
```

`fetch` and `land` refuse while that lane's loop still runs (add `--force` only for a branch you know is finished), refuse a dirty main checkout, and refuse a test count below the baseline.

Watch the lane logs with `Monitor` (grep for `Stopped|parked|Traceback`), never a sleep loop. Land each lane as soon as it stops, and keep runs short (`--max-issues 3`): a lane branch of 5 to 14 tickets rebased onto a busy `main` hit a conflict on almost every commit. Before parallel lanes, check the repo's tests use per-process temp folders and free ports, or gates collide.

## Gates with many lanes

The gate is the one shared bottleneck: each `./verify.sh` runs 4 to 5 CPU-bound processes, and past about 4 at once the load passes 20 and timing-sensitive tests flake. Don't cap lanes; queue gates.

- `lane.py` and `overnight-loop.py` take a slot from `bin/gateslot.py` (flock files in `~/.cache/gate-slots/`) around every gate; a dead holder frees its slot, and the wait doesn't count against `--verify-minutes`.
- `GATE_SLOTS` is the gate count (default 2, `0` turns the queue off); `lane.py land` also gets one reserved slot. Tune it by `uptime`: keep the 1-minute load under the core count. Set it in the shell that starts the lanes.
- Workers iterate with the repo's one-suite test script and gate once, at the end. Run a hand gate as `gateslot.py [--land] -- ./verify.sh`.
- Before many lanes, check RAM (a Godot process is a few hundred MB), that tests use free ports and per-process temp folders, and that a gate's own ports can't collide.

## 4. Review and land

For every finished branch:

1. `lane.py fetch`. If it stops on conflicts, a Sonnet subagent resolves them in that worktree, keeping both sides' behaviour.
2. A Sonnet subagent reviews it against each issue's _Done when_ and runs the gate. If the change is visible, it also runs the repo's capture scripts on the Mac's display and reads the PNGs.
3. Ask DeepSeek for a second opinion on every branch with real logic in it, and always on large or risky ones (architecture, networking, auth, data): `pi-ask.py --session review-<x> --dir <a separate detached worktree> @prompt.md`. A different model family catches different bugs: its review of a 20-commit refactor found four real bugs that Sonnet passed.
4. Fix small leftovers yourself; ticket the rest. Then `lane.py land`.

## Throughput: what kept a 20-lane night moving

The gate is the bottleneck, not coding. Spend gates only where they buy safety.

- **Land without a second gate** (`lane.py land --no-verify`) when the rebase onto main is clean and the lane's own gate passed. Run the full gate at landing only when the rebase had conflicts or the lane's gate evidence is missing. Every 5 landings, gate main in its own detached worktree (never the main checkout, which landings change under it).
- **Skip a lane's startup gate** on a tree that already passed: `gateslot.mark_passed()` records a tree, the loop checks `already_passed()`. Mark main after each landing.
- **Serialise landings with a lock** and script the routine: rebase, check `shard_weights` duplicates, land, restart the lane if its label still has open tickets. Run long chains with `nohup`; a harness background task dies at 30 minutes.
- **Split a multi-ticket label into parallel lanes** by file area as soon as a lane has more than two tickets queued. Keep only true dependencies (a guard test after the fixes it guards) in one lane. Move only open tickets without `overnight:done`: `lane.py land` closes an issue only if it still carries the lane's label.
- **Long nights need `--issue-minutes 180 --hours 12`.** With many lanes a worker's own gate waits for a slot inside its 90-minute default, and Sonnet workers timed out with nothing committed; `--hours` (default 8) quietly stops a lane starting new tickets.
- **Review by risk.** DeepSeek reviews every branch with logic; skip review for data-only or test-only branches. Land a non-blocking finding and file it as a follow-up on the same label; drop nits.
- **Check the diff has code.** DeepSeek workers sometimes stop mid-task ("Now I'll implement…") and the loop records only `progress.md`; a review that finds no code means unpark and rerun. Give large UI or networking tickets to Sonnet workers.
- **`--budget` reads the gateway's whole counter,** so with N lanes each lane sees every lane's spend: set it to the night's total, not a per-lane share. A negative gateway offset (Greg's workaround to lift the cap) disables it.
- **Gate slots:** measure load while gates run. On 16 cores, 4 slots plus a landing slot reached load 57 and gates timed out; 3 held load near 15.
- **One watcher** for lane state changes, DeepSeek answers and landing results, re-armed every 30 minutes. Key "seen" results by content, not mtime (GNU `stat` breaks `-f %m`).

## 5. Keep the queue full

When lanes drain, fan out read-only audits in parallel, each a subagent with one lens: architecture against Greg's rules and the ADRs, tests and coverage, performance (measured, not guessed), agent tooling, and a visual pass on fresh captures. Turn verified findings into tickets and start the next round. Stop when only `manual` tickets remain, then report: what landed, what each manual ticket needs from Greg, real spend.

## Subagents

- **Models:** Sonnet first, for code, reviews, rebases and audits, as subagents and as loop workers. DeepSeek next, and freely: it is cheap, not a reserve for hard problems. A whole review of a 20-commit refactor cost $0.05 at DeepSeek's prices (the gateway's daily cap counts about twice that), and off-peak hours halve it. Use it for every second-opinion review, for extra lanes (`--harness pi`) when Sonnet lanes are busy or rate-limited, and for bulk reading. Only its daily cap and Greg's `--budget` limit it. Haiku for mechanical work only: status sweeps, running captures and listing results.
- **Every prompt** names one worktree with absolute paths, says what not to touch (the main checkout, other lanes), says no AI attribution lines and no pushing, and ends: "Your FINAL message must be the report itself, under N words". A subagent once returned the word "placeholder"; when a report is empty, inspect its worktree and run the gate yourself.
- **Background:** start subagents and pi-ask in the background, keep orchestrating, and act on each notification.

## Lessons that cost a night to learn

- A test that boots the real game can overwrite the player's saved files; tests use their own folders.
- `button.pressed.emit()` misses a control drawn over the button; UI tests click at the button's centre.
- A tiling window manager (AeroSpace) resizes game windows; captures render at a fixed content-scale size.
- Each loop commit appends to `progress.md`; `lane.py fetch` sets `merge=union` so rebases don't conflict there.
- A worktree's first gate can fail on import-order errors a warm `.godot/` cache hides; if the repo has such an open bug, run `godot --headless --path . --import` once in the worktree before `lane.py land`.
- Two lanes started in the same minute share a branch name; `lane.py fetch` gives each its own.
- When one side renamed a file and the other edited it, resolving needs `git rm` of the old path, which the auto-mode permission check refuses to a subagent. Run that one command yourself, and tell subagents to report such paths rather than work around the refusal.
- A loop worker ran `pkill -f godot` to clear its own tests and killed every other lane's gate at once (all shards exit 143). Every subagent and worker prompt, and the repo's `CLAUDE.md`, must forbid killing processes by name.
- A subagent filed six tickets with each body shifted onto the next title, and five lanes built the wrong things. After any batch filing, compare each `gh issue view` title with its body before starting a lane.
- DeepSeek found new bugs on the fix rounds too, not only the first review (snapshot bloat from a lazy ghost, a replay that lost a restored key). Recheck a fix round with the same `pi-ask` session.
- Reviewers pass tests that can't fail. Ask them to prove each new test by mutation: remove the line under test and watch it fail.
- In a networked game, effects driven by local signals never reach guests, who only apply snapshots. Ask reviewers of any sound, shake or popup change how a guest gets it, and whether a guest joining mid-run replays old events.
- In zsh an unquoted `$ARGS` is not word-split, so `lane.py start x -- $S` passes one argument and the loop dies at once. Write the arguments out.
- A ticket parked only because its _Done when_ asks for an orchestrator capture is finished work: recover the commit (`git branch parked-N <sha>` in the lane clone, fetch, cherry-pick) instead of rerunning it.

## Big features: a staged pipeline

For a feature with real design in it (new maps, a new mode, a networking change), don't ticket straight from the request. Each stage gets a review before the next:

1. **Concept:** a Sonnet subagent reads the code and pitches options; DeepSeek checks the pitch against the code. It caught claims that would have made a map unplayable.
2. **Design:** one spec per piece with real numbers and a verification list; DeepSeek reviews it, the designer revises, DeepSeek rechecks. Two rounds caught jump physics, spawns in traffic and unreachable zones before any code.
3. **Groundwork tickets** shared by every piece, landed first so the pieces don't collide.
4. **Build** one piece per lane, then **verify**: scripted drives of the spec's checks, captures judged for the intended feel, Sonnet and DeepSeek reviews.

Put the approved designs and any ADR in the repo before the build tickets, so workers read them.
