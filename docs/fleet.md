# The fleet: how Greg runs many agents through one conversation

What the setup is, how a ticket moves through it, why it is built this way, and what it takes
to build again. The fictional names come from Battlestar Galactica; each role's rules live in its
own doc (see "Where each piece lives").

## The roles

| Fictional | Technical | What it is | LLM? |
|---|---|---|---|
| President | user | Greg. Talks to one session, the Commander, from a laptop or a phone. | human |
| Commander | supervisor | One long-lived Claude session over every repo. Relays Greg's orders, handles what the scripts can't decide, finds root causes and adds guards. | yes |
| XO | watchdog | A script beside the Commander. Wakes it only when something needs a decision. | no |
| Chief | control plane | A script per repo. Owns the run's state: which ticket starts, when a builder is stuck, landing, the canary. Writes every change as an event. | no |
| CAG | judgement desk | One interactive Claude session per repo. Hosts the builder subagents and makes the calls that need judgement: reviews, failures, conflicts, new tickets. | yes |
| Viper | worker | A builder, reviewer or fixer for one ticket, started fresh: a Claude subagent inside the CAG, or a pi lane on DeepSeek. | yes |

```
                 President (Greg)
                        |
                    Commander <---- XO  (forwards events, watches the Chiefs' heartbeats)
                   /         \
     Chief -> CAG (gridkeep)   Chief -> CAG (loser-picks)
       |        |                |        |
     lands    Vipers           lands    Vipers
```

## How a ticket moves

1. Greg files or approves a ticket with a priority label. The Commander writes his standing
   orders ("throughput first", "no DeepSeek until 07:00") into its run log and the CAGs'
   restart prompts.
2. The Chief sees a free builder slot and a ready ticket, and offers it to the CAG: at the end
   of the CAG's turn through a Stop hook, or by message when the CAG is idle.
3. The CAG starts a Viper for it. The Viper builds in its own git worktree with a fresh context,
   runs the tests, and ends. Another Viper reviews.
4. On a passing review the Chief lands the branch, proves it reached `origin/main`, and runs the
   canary. A red canary gets one rerun, then reopens the red-main ticket; builders keep going.
5. Every step is an event in the Chief's log. The XO forwards the ones that need a decision to
   the Commander, which fixes the problem, finds why it happened, and adds a guard in code.

Steps 2, 4 and 5 are partly built; see "Status".

## Why it is built this way

- **Code drives; LLMs decide.** Waiting, polling, counting slots, landing and timers are
  deterministic work, so a script does them. An LLM does one unit of judgement and returns. When
  an LLM held the clock, it chose to wait on a canary four times in one day despite its brief.
- **Interactive sessions only.** Claude runs as interactive sessions on Greg's subscription:
  headless `claude -p` drains the same quota 1.8-2.9x faster. Builders are subagents of an
  interactive CAG for the same reason, which is why the CAG remains.
- **Messages, not keystrokes.** Typing into a terminal pane and reading the screen back loses
  text when the pane is busy and misses prompts nobody sees. Sessions are reached through Claude
  Code's own channels: Stop hooks at turn end, the cross-session messaging socket when idle, and a
  PermissionRequest hook that answers prompts instead of letting them sit.
- **One source of truth.** The Chief's event log is the run's state; the XO and the Commander read
  it rather than each guessing from screens. Two watchers guessing separately is how a false
  "main red" alarm fired.
- **One ticket, one fresh builder.** A Viper never carries context from one ticket to the next.
  Small contexts are cheap and nothing leaks between tickets.
- **Every LLM is ephemeral.** The CAGs and the Commander roll at a token limit: they write what
  they know to disk and restart from a fixed message (`docs/claude-shifts.md`). Nothing is
  compacted. Tickets and labels hold the work, repo docs hold lessons, the Commander's run log
  holds orders.
- **One entry point.** Greg talks to the Commander only, so he never juggles terminals.
- **Limits live in code.** Caps on builders, load, quota and landings are hooks, scripts and
  labels. A prompt rule failed twice in one night.
- **Every fix gets a root cause and a guard** (`docs/commander.md`), so the same stall can't
  cost time twice.

## How it got here

The first version (11-17 to 11-20) put an LLM at the centre: the CAG picked tickets, launched
builders, watched gates and landed, and the scripts only woke it. Over 47 hours (11-18 22:16 to
11-20 21:05) the logs show 41 incidents:

| Cause | Incidents | Time lost |
|---|---|---|
| The LLM orchestrator chose wrong (waited, forgot a rule) | 9 | ~2.3 h |
| Pane glue (lost text, unseen prompt, notice lost on restart) | 6 | ~2.3 h |
| Load, orphan processes, wrong host, sleep | 10 | mostly untimed |
| Tests, landing train, canary | 6 | ~6.8 h |
| Bugs in our own scripts | 8 | ~5.8 h |
| Other (a spend cap halted DeepSeek) | 2 | ~7 h of pi |

The first two rows are the design itself and the fragility Greg felt: steady hand-holding. The
rest came from new code going live under load, which any design pays for. So the fix keeps the
parts and moves the control plane into code (11-20 review:
`~/Git/notes/llm/software-factory-alternatives-2026-11-20.md`). Rejected:

- **Headless workers driven by a scheduler** (the common robust pattern): quota cost.
- **Harbor**: an agent evaluation harness. It runs agents in containers and scores them; it has
  no tickets, landing or coordination.
- **Temporal, Hatchet, DBOS**: the right pattern, but a server and a rewrite for one person.
- **GitHub merge queue**: needs an organisation account; both repos are personal.
- **An LLM coordinator over tmux** (Gas Town and similar): the design being moved away from.

## Building it again

What you need:

- **Claude Code** with hooks (Stop, UserPromptSubmit, PermissionRequest) and cross-session
  messaging, on a subscription.
- **A terminal multiplexer that reports session state.** Herdr's `hc` gives each terminal's
  state, running tasks and turn count as `hc events`, across machines over ssh.
- **GitHub issues** with `priority:*`, `size:*` and `stage:*` labels as the work's state.
- **Git worktrees**, one per ticket, and a lander script that rebases, tests, pushes and prints
  `LANDED <sha>` or `FAILED <step>`.
- **A Chief**: a loop with a lock and a heartbeat that reads the queue and labels, offers work,
  lands, runs the canary and writes events. gridkeep's `tools/land/pilot.sh` is the working model.
- **An XO**: a loop that forwards events to the supervisor and checks the Chiefs are alive.
- **Roll machinery**: a token threshold, a drain message, and a restart prompt per session.

Order: lander first, then the Chief, then a CAG that only reviews and builds, then the XO and a
Commander once there is more than one repo.

## Where each piece lives

- Commander rules, root causes, the arm command: `docs/commander.md`.
- Rolling sessions: `docs/claude-shifts.md`.
- The XO: `bin/control-loop.sh`. Its next step: `.scratch/fleet-events/`.
- The Chiefs: gridkeep `tools/land/pilot.sh`; loser-picks `tools/chief`, being ported from it
  (lp #398).
- GitHub quota: `docs/github-api.md`.

## Status (2026-11-20)

Live: Commander, XO, both CAGs and their Vipers, rolls for both, loser-picks' Chief as a waker
(since 16:53). The move to code as control plane is filed as P0s:

- loser-picks: the Chief starts slots (#406), hands back reviews (#407), lands (#408), offers work
  at turn end (#424), messages over the socket (#425 spike, #428), writes events (#426), owns the
  canary (#427); long runs capped by process group (#310).
- toolbox: the XO forwards the Chief's events (`.scratch/fleet-events/`).
