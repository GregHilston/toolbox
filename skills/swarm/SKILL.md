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

## 4. Review and land

For every finished branch:

1. `lane.py fetch`. If it stops on conflicts, a Sonnet subagent resolves them in that worktree, keeping both sides' behaviour.
2. A Sonnet subagent reviews it against each issue's _Done when_ and runs the gate. If the change is visible, it also runs the repo's capture scripts on the Mac's display and reads the PNGs.
3. Ask DeepSeek for a second opinion on every branch with real logic in it, and always on large or risky ones (architecture, networking, auth, data): `pi-ask.py --session review-<x> --dir <a separate detached worktree> @prompt.md`. A different model family catches different bugs: its review of a 20-commit refactor found four real bugs that Sonnet passed.
4. Fix small leftovers yourself; ticket the rest. Then `lane.py land`.

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
