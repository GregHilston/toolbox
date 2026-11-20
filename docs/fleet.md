# The fleet: how Greg runs many agents through one conversation

A short description of the whole setup, with the fictional names (from Battlestar Galactica)
beside the technical ones. Rules for each role live in their own docs; this one explains the
shape and the reasons.

## The roles

| Fictional | Technical | What it is | LLM? |
|---|---|---|---|
| President | user | Greg. Talks to one session, the Commander, from a laptop or a phone. | human |
| Commander | supervisor | One long-lived Claude session that watches every orchestrator, relays Greg's orders, finds root causes and adds guards. | yes |
| XO | watchdog control loop | A script beside the Commander. Polls the orchestrators and wakes the Commander only when something is wrong. | no |
| CAG | orchestrator | One Claude session per repo. Picks tickets, starts workers, reads reviews, lands branches. | yes |
| Chief | dispatcher control loop | A script beside each orchestrator. Watches its workers, gates and landings, and wakes it only for a decision. | no |
| Viper | worker | A short-lived builder, reviewer or fixer for one ticket: a Claude subagent or a pi lane on DeepSeek. | yes |

```
            President (Greg)
                   |
              Commander ---- XO
             /           \
    CAG (gridkeep)    CAG (loser-picks)
       |   \              |   \
    Vipers  Chief      Vipers  Chief
```

## How a night flows

1. Greg tells the Commander what matters ("throughput first", "no DeepSeek until 07:00") and
   goes to bed. The Commander writes each order into its run log and passes it to the CAGs.
2. Each CAG picks the highest-priority ticket and launches a Viper to build it, another to
   review it, and lands it when the review passes. The Vipers do almost all the work and
   then end.
3. The Chief watches that work with no LLM: a builder exited, a review came back, a gate
   went red. It wakes its CAG with one line naming the next step, so the CAG never spends
   tokens waiting.
4. The XO watches the CAGs the same way: a CAG blocked on a question, no Claude in its pane,
   load too high, nothing landed in 90 minutes, a red main left open, the GitHub quota low.
   It wakes the Commander with one line, so the Commander sleeps between problems.
5. When woken, the Commander fixes the problem, finds its root cause, and adds a guard in
   code so it can't happen again (`docs/commander.md`).

## Why it is built this way

- **Context is the cost.** An LLM re-reads its whole context on every turn, so a session
  that keeps growing gets slower and dearer. Vipers do the heavy reading and writing in
  their own short context and hand back a summary; the CAG's and the Commander's contexts
  grow slowly.
- **Every LLM is ephemeral.** CAGs and the Commander roll on a schedule: at a token limit
  they write what they know to disk, clear themselves, and restart from a fixed message
  (`docs/claude-shifts.md`). Nothing is compacted and nothing depends on a chat's memory.
- **Memory lives on disk.** Tickets and their stage labels hold the work's state; repo
  docs hold the lessons; the Commander's run log holds Greg's orders, the watch list and
  open questions, across dates. A fresh session reads those and carries on.
- **One entry point.** Greg talks to the Commander only. It knows every CAG, relays orders,
  and answers "how's it going?" for the whole fleet, so he never juggles terminals.
- **Scripts guard the LLMs.** LLMs loop, stall on a question, or die mid-task. The XO and
  the Chiefs are plain scripts: deterministic, cheap, and not subject to those failures.
  They write a heartbeat file each pass, alert once per event, and hold a lock so two never
  run on the same target. When an LLM goes quiet, a script notices.
- **Waiting costs nothing.** Polling by an LLM re-reads its context each time; polling by a
  script is free. Moving the waiting into scripts is most of the gap between loser-picks (47
  orchestrator calls per landed ticket) and gridkeep (24), whose `pilot.sh` already acts as
  its Chief.
- **Limits live in code, not prompts.** Caps on builders, load, quota and landings are
  enforced by hooks and scripts; a prompt rule failed twice in one night.

## Where each piece lives

- Commander rules, root causes, the arm command: `docs/commander.md`.
- Rolling sessions: `docs/claude-shifts.md` (`bin/shift-arm`, `bin/orchestrator-roll`,
  `bin/commander-roll`, the Stop and UserPromptSubmit hooks).
- The XO: `bin/control-loop.sh`, started detached, waking the Commander's pane.
- The Chiefs: gridkeep `tools/land/pilot.sh`; loser-picks' is being built (lp #397, #398).
- GitHub quota: `docs/github-api.md`.

## Status (2026-11-20)

Live: Commander, XO (as a detached control loop), both CAGs and their Vipers, CAG rolls.
Being finished: Commander rolls (built, live trial pending) and loser-picks' Chief.
