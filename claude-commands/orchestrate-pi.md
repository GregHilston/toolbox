# Orchestrate GitHub Issues with pi Workers

Same job as `/orchestrate`, with the implementation moved off Claude and onto
local `pi` processes talking to DeepSeek. You stay the orchestrator: you preflight,
you spawn, you verify, you merge, you own every `gh` write.

**Read `/orchestrate` first — Steps 0 through 3 and the whole bookkeeping half are
identical and are not repeated here.** Issue selection, `prep:ready` labels, the
worktree probes, the cwd traps, queue planning, merge verification, `Closes #N`
trailers, filing agent findings, the closing report: all of it applies unchanged.
This file covers only what differs when the worker is a `pi` subprocess instead of
a subagent. Two copies of the preflight would drift within a month.

## Usage

```
/orchestrate-pi --label prep:ready              # the default queue
/orchestrate-pi 16 23 41                        # these issues
/orchestrate-pi --workers 6                     # concurrency (default 4, ceiling 8)
/orchestrate-pi --model flash                   # pro (default) | flash
/orchestrate-pi --thinking max                  # off | low* | high (default) | max
```

`low` exists on Flash only — Pro's ring is `off → high → max`. See the model table
in `~/Git/toolbox/dot/pi/CLAUDE.md`.

### How many workers, and what actually binds

**The default is 4 and the ceiling is 8.** Raised from 2 once the work moved to a
metered DeepSeek key on a 16-core M4 Max with 128GB — but the machine was never
the binding constraint, and reaching for 8 because the hardware allows it is how a
run ends with eight branches nobody has read.

Three things bind, in ascending order of how often they actually bite:

- **The host, and it binds last.** Each commit runs the pre-commit hook: gdlint
  plus a headless Godot GUT suite for `.gd`/`.tscn`/`data.jsonc` (~50s), pytest
  with coverage for Python (~110s), about three minutes for a commit touching
  both. These are near enough single-threaded, so N workers want N cores and 16
  is not the wall. Memory is not the wall either. Two host-level collisions are
  real, though, and neither is about core count: anything that starts the dev
  server collides on **port 8000** (which the oMLX model server may also own —
  see `doctor.py`), and `run_ui_screenshots.sh` opens a rendering context per
  run, which is fine at small N and untested at 8.
- **Merge conflicts, which scale with subsystem overlap and not with N.** Eight
  workers across eight unrelated modules merge cleanly; three inside
  `godot-client/scenes/game/` will fight, and you merge them serially regardless.
  `/orchestrate`'s Step 3 already says to serialize issues touching the same
  subsystem — at higher N that stops being advice and becomes the thing that
  decides your real concurrency. Count *disjoint subsystems* in the queue, and
  set `--workers` to that, not to the core count.
- **Your own review throughput, which is the one that actually binds.** Every
  finished worker costs you a diff to read, a Claude review subagent, a feedback
  pass back through `--continue`, and a merge. That is Claude tokens and your
  attention, and it does not parallelize the way the workers do. Eight workers
  landing together is eight diffs queued behind one reviewer.

So: **pick N from the queue's shape, not the machine's.** Four disjoint issues,
four workers. Eight issues that all live in the combat screen, still two or three.
And if you are ever tempted to raise N to finish sooner, the cheaper trade is
almost always to keep N where it is and not skip the review loop in Step P3 —
that loop costs under two cents and has caught things the green suite did not.

## Why this split exists

Claude Code does the deciding: reading issues, planning the queue, reviewing
diffs, merging, `gh`. That is a small number of tokens on your Claude
subscription, which is what "ordinary, individual usage" in Anthropic's Claude
Code terms contemplates. pi does the grinding, billed to your own DeepSeek key.

**Never `/login` to Claude inside pi.** That routes Claude traffic through a
third-party harness on subscription credentials, which is metered separately
against Agent SDK credits and is not what this design is for. pi's provider here
is `deepseek`, always. If a worker ever reports an Anthropic model, stop the run.

---

## Step P1 — Preflight the worker, not just the repo

Do `/orchestrate`'s Step 2 preflight in full, then these four. **All four fail
silently or misleadingly**, which is why they are worth a probe each.

### P1a. `pi -p` never prompts for project trust

Non-interactive modes (`-p`, `--mode json`, `--mode rpc`) show no trust prompt. With
no saved decision they fall back to `defaultProjectTrust: "ask"` and **ignore every
project resource** — `.pi/settings.json`, project extensions, and the per-project
permission config Step P1b depends on. Nothing errors. The run just behaves as if
those files were absent.

**Pass `--approve` on every worker invocation.** Verify once:

```bash
cd <worktree> && pi --approve --offline -p 'Reply with exactly: OK'
```

### P1b. An unattended worker cannot create files by default

The global permission config sets `"write": {"*": "ask"}`, and `ask` with no UI
resolves to **`confirmation_unavailable` — blocked**, not queued and not prompted.
So a worker can `edit` existing files but cannot `write` a new one, and the failure
surfaces as the model getting a denial mid-task and improvising around it.

Fix it per worktree, not globally, with a project-scope config at:

```
<worktree>/.pi/extensions/pi-permission-system/config.json
```

```json
{ "yoloMode": true }
```

`yoloMode` is a composition-stage **ask→allow rewrite only**. The extension's own
docs state it plainly: *"An explicit `deny` still denies under yolo."* So the global
denies — `*.env`, `~/.ssh/*`, the Reddit cookie — survive, and this only lifts the
`ask` gates. That is the whole reason to reach for yolo here rather than the
alternative below.

This file needs `--approve` to load at all (P1a). Add `.pi/` to the worktree's
ignore or delete it before merging — it is scaffolding, not part of the change.

### P1b-bis. Arm the guardrails in the same breath

`yoloMode` lifts the `ask` gates; it does not stop a worker doing something it was
told not to. Write a second file into the same `.pi/`:

```bash
echo '{}' > <worktree>/.pi/guardrails.json
```

That arms `orchestration-guardrails`, which turns the prompt's prohibitions into
`tool_call` blocks: no `git push`, no `checkout main`/`merge`/`rebase`, no
`--no-verify`, no `gh` write subcommand, no `pi install`, no repointing
`core.hooksPath`, and no rewriting `.pi/` from either the write tool or the
shell. The model gets the reason, not a bare refusal — *"Never push. A pre-push
hook deploys the API… the orchestrator pushes."*

The push rule asks to terminate the run, but **that is conditional**: pi stops
early only when *every* finalized call in a batch is terminating, and parallel
tool execution is the default. A push issued alongside another tool call is
blocked but does not stop the run. The block always holds; the stop is a
best-effort extra.

**The threat model is a careless worker, not an adversarial one.** `bash -c "git
push"`, `eval` and `$(...)` all defeat these, and closing that would mean parsing
the shell rather than reading it. Confinement is the sandbox's job.

`{}` is the right content: rules merge onto the defaults, so a worktree that adds
one rule still gets the eight that ship. Add project-specific ones only when the
repo needs them:

```json
{ "bash": [{ "pattern": "^\\./export_macos\\.sh", "reason": "Interactive; it will hang you forever." }] }
```

**Keep saying it in the prompt as well.** The guardrail stops the action; the
prompt is what stops the worker wasting a turn discovering the boundary.

**Do not reach for `--no-extensions` instead**, even though it is cheaper in tokens.
It unloads the permission system entirely, and pi's built-in tools have no gate of
their own — you would end up *more* permissive than yolo and lose the deny list with
it. If tokens are the concern, trim with `--no-skills --no-prompt-templates`, or
`-ne` plus an explicit `-e` path to just the permission extension.

### P1c. pi has no sandbox, and a worktree is not one

pi's security docs are explicit: built-in tools read, write, and run shell commands
with the full permissions of the pi process, and unattended work belongs in a
container or VM. A git worktree is a *merge-conflict* boundary, not a security one.

What you actually have protecting an overnight run: the surviving `deny` list, the
worktree limiting accidental blast radius, and the repo being one you trust. What
you do not have: protection from prompt injection via repo content, or from a
worker deciding to run something destructive. `DEEPSEEK_API_KEY` is in that
process's environment.

**Tell the user this before the first overnight run**, once, and let them decide.
Do not bury it in the closing report.

### There is a sandbox now, and it is not yet ready for unattended use

pi ships an official `sandbox` extension built on `@anthropic-ai/sandbox-runtime`
— `sandbox-exec` on macOS, bubblewrap on Linux, the same mechanism Claude Code
uses. It is installed at `~/.pi/agent/extensions/sandbox`. Crucially it sandboxes
the **bash tool** while pi runs on the host, so the worker keeps `godot`, `uv` and
the rest of the host toolchain — which is why an earlier plan to build a Linux
container image for this was wrong.

It is **parked outside the auto-discovery root**, at
`~/Git/toolbox/dot/pi/extensions-available/sandbox`, and must be loaded by hand:

```bash
cd <worktree> && pi -e ~/Git/toolbox/dot/pi/extensions-available/sandbox …
```

That placement is deliberate. Its `package.json` carries a `pi` manifest and pi
auto-loads any subdirectory that has one — no `-e` needed — while its
`DEFAULT_CONFIG` is `enabled: true`. Left in the extensions directory it turned
sandboxing on for every pi session on the machine, and a global
`{"enabled": false}` did **not** turn it back off; only removing the directory
did. `node_modules` is gitignored, so run `npm install` there first.

with `<worktree>/.pi/sandbox.json`:

```json
{ "enabled": true, "filesystem": { "allowWrite": ["."], "denyRead": ["~/.ssh", "~/.aws"] } }
```

Measured 2026-08-27: **filesystem confinement works** — a write to a path outside
`allowWrite` did not land. Two things stop it being the default here:

- **A denied write hangs the worker** rather than returning an error promptly. It
  had not returned after two minutes. Enabling this unattended would trade a
  silent-death failure for a silent-hang failure, which is the exact class the
  status file was built to remove. `orchestration-status` makes the hang *visible*
  now, so this is diagnosable rather than mysterious — but it is not solved.
- **It cannot be disabled by config**, only by not loading it. See above.
- **Network domain filtering hung a run outright** and was not investigated. Use
  filesystem-only config until someone does.

So: worth using attended, worth watching, not yet worth trusting overnight. See
issue #82 in gridkeep for the open work.

### P1d. Establish the token floor

Every tool schema and context file is re-sent on every request, and now it is
billed. Measure before spawning:

```bash
cd <worktree> && pi --approve --mode json -p 'Reply with exactly: OK' 2>/dev/null \
  | python3 -c "import sys,json;[print(json.loads(l).get('message',{}).get('usage')) for l in sys.stdin if '\"usage\"' in l][-1:]"
```

Read `totalTokens`, not `input` — `input` is only the uncached remainder and will
understate the real prompt by an order of magnitude. In `~/Git/gridkeep` expect
~16k. Multiply by your expected turn count per issue and tell the user the estimate
before the run, not after — but see the cost note in Step P3: cache reads make the
real figure roughly 30x lower than that arithmetic suggests.

### P1e. Set PI_STATUS_FILE, and never diagnose a worker by log size again

Export `PI_STATUS_FILE=<worktree>/.pi/status.json` on every spawn. The
`orchestration-status` extension then rewrites that file on every turn and every
tool call — atomically, so it is always safe to read mid-write:

```json
{ "phase": "tool", "pid": 51035, "turn": 42, "toolCalls": 26,
  "currentTool": "bash", "lastActivityAt": "2026-08-27T16:24:03.114Z",
  "lastBlocked": "bash @ turn 12",
  "usage": { "totalTokens": 3562885, "cacheRead": 3453824, "costUsd": 0.0316 } }
```

**This exists because a dead worker and a thinking worker are indistinguishable
from outside.** A worker that dies on spawn writes a 0-byte JSONL; one thinking
hard for four minutes also writes nothing new. In the run this was built from,
two dead workers were reported as "still running" twice before anyone ran `ps`.

Poll all workers at once:

```bash
for f in <repo>/worktrees/*/.pi/status.json; do
  python3 - "$f" <<'EOF'
import json,sys,datetime
s=json.load(open(sys.argv[1]))
age=(datetime.datetime.now(datetime.UTC)-datetime.datetime.fromisoformat(s["lastActivityAt"].replace("Z","+00:00"))).total_seconds()
print(f'{sys.argv[1].split("/")[-3]:24} {s["phase"]:9} turn {s["turn"]:>3}  {s.get("currentTool") or "-":8} {age:6.0f}s ago  ${s["usage"]["costUsd"]:.4f}')
EOF
done
```

Read it like this:

- **No file at all** — it never started. This is the spawn bug, not a slow turn.
- **`lastActivityAt` older than ~120s while `phase` is not `settled`** — genuinely
  stuck. Read the log before killing.
- **`lastBlocked` set** — the guardrails refused something; the worker may be
  improvising around a boundary and is worth a look.
- **`phase: "settled"` or `"shutdown"`** — done; go verify the branch.

It also retires log-scraping for telemetry: `usage` here is the running total, so
`.claude/pi-usage.py` becomes a cross-check rather than the only source.

---

## Step P2 — Spawning a worker

Write the prompt to a file and pass it with `$(cat …)`. Do not inline it — worker
prompts are Markdown full of backticks and newlines, and shell quoting mangles them
quietly. Same lesson as `gh issue create --body-file`.

```bash
cd /abs/path/to/worktrees/issue-16 && \
  PI_STATUS_FILE=/abs/path/to/worktrees/issue-16/.pi/status.json pi \
  --provider deepseek --model deepseek-v4-pro --thinking high \
  --approve \
  --session-id issue-16 \
  --mode json \
  -p "$(cat /abs/path/to/.claude/pi-prompts/issue-16.md)" \
  > /abs/path/to/.claude/pi-logs/issue-16.jsonl 2>&1
```

**Write the prompt file in a separate, earlier call.** A heredoc and a backgrounded
`pi` in one command silently produces nothing: the file is written, the harness
reports the command as running, no process ever starts, and the redirect target sits
at 0 bytes with no completion notification. It is indistinguishable from a long
turn, and it cost two stalled workers in one run. One call writes the file; the next
call is a bare `pi` invocation and nothing else.

Run it with `run_in_background: true` — you are re-invoked when it exits, which is
what keeps worker slots rotating. Absolute paths everywhere; the Bash cwd persists
between calls and `/orchestrate`'s Step 2a-bis catalogues what that has already cost.

**The prompt is `/orchestrate`'s Step 4 prompt, unchanged**, minus the parts that
assume a subagent. Keep every one of: the verbatim issue body, "check whether it
already shipped", the `Closes #N` trailer instruction, the decisions-it-must-make-
alone list, never-push/never-merge/never-`gh`-write, the named forbidden interactive
scripts, and the other agents' issue numbers.

Three additions specific to pi:

- **State the model and that thinking is on.** A worker that does not know it has a
  thinking budget will not use it.
- **Ask for the final report as the last message**, in the shape Step 4 requires.
  There is no return value here — you read it out of the log.
- **Forbid `/login`, `pi install`, and any edit to `~/.pi`.** A worker has no reason
  to touch pi's own configuration, and one that does can change the next worker's
  behaviour.

### Iterating with a live worker

To push back on a worker without re-sending its whole context:

```bash
cd <worktree> && pi --approve --continue \
  -p 'The GUT suite fails on <file>. Fix it and re-run; do not disable the test.'
```

**Do not add `--session-id` here.** pi refuses the pair outright —
`Error: --session-id cannot be combined with --continue`. `--session-id` is
create-if-missing, for *starting* an addressable session; `--continue` resumes
one. Sessions are keyed by project directory, so a bare `--continue` from the
worktree's own cwd is unambiguous — one worktree, one session. If you need to
name it explicitly, `--session <id>` is the flag that accepts one.

Cheaper than a fresh worker, and it keeps the prior reasoning in context. This is
also how the review loop closes: a fresh Claude subagent reviews
`git diff main...HEAD`, and its findings go back to the *original* worker this
way, so the agent that enacts them still has its own reasoning in context.

---

## Step P3 — Verification is stricter here, not looser

`/orchestrate`'s Step 5 applies in full. Two things change the weighting:

**You cannot see the worker think.** With a subagent you at least get a coherent
narrative. Here you get a JSONL log and a final message. Treat the report as a
claim, and let the diff be the evidence — read it yourself. Spot-checking the
highest-consequence claim stops being good practice and becomes the load-bearing
step.

**Review with a Claude subagent, not another pi.** One adversarial review of
`git diff main...HEAD` is a single cheap read where judgement matters most, and it
is the right place to spend Claude tokens in a design whose whole point is spending
them sparingly. Give it the worktree path, the sandbox rule, and the failure modes
specific to *this* issue — generic "review this" gets generic results.

### Always close the loop back to the original worker

**Do this on every issue. It is the highest-value thing in this command and it is
very nearly free.**

The loop is: pi worker commits → you verify → a **fresh Claude subagent** reviews
`git diff main...HEAD` → its findings go back to the **same pi session** via
`--continue` → the worker enacts what it agrees with → you re-verify → merge.

Feed the findings back to the *original* worker rather than a new one, because it
still holds its own reasoning and can say "I disagree, here is why". Measured over
three issues, a feedback pass costs **$0.005–$0.014** and runs at a **99.4% cache
hit rate** — `--continue` resumes a warm session, so billed input collapses (3,993
tokens on one feedback pass against 44,113 for the worker that preceded it). It is
the cheapest work in the entire run.

**Frame it as a decision, not a work order.** Tell the worker to enact only what it
agrees with and to say why it rejects the rest. Disagreement is a valid outcome and
you want it: across three issues the workers rejected two suggestions, and were
right both times — once catching that the reviewer's proposed one-line guard would
have broken an unrelated code path on first use.

What this loop actually caught, in one short run: a test that would have passed
against a component rendering nothing at all, a fix-shaped-like-the-bug
anti-pattern, and seven stale comments and captions describing behaviour that no
longer existed. None of it was found by the suite, which was green throughout.

**Do not skip it to save time.** It roughly doubles wall-clock per issue and adds
under two cents. If you are ever tempted to trade it away, trade away a worker slot
instead.

Before merging, confirm the worker left no scaffolding: the `.pi/` config from P1b,
stray log files, `--session-id` artifacts.

### Report what it cost

`--mode json` emits usage per turn, on `message_end` events — sum those, not
`turn_end`/`agent_end`, which repeat the same numbers. Each carries pi's own
`cost` object; prefer it to recomputing from a price table.

**Read `cacheRead`, not just `input`.** Measured over two gridkeep issues on
Flash/`high`: 95% and 98% cache hit rates, and cache reads bill at $0.0028/M
against $0.14/M for fresh input. The two issues cost **$0.0103 and $0.0316** —
four cents for both, against a pre-run estimate of $0.15–0.35 *each*. A cost
line that reads only `input` will overstate a run by more than an order of
magnitude.

`gridkeep/.claude/pi-usage.py` prints the whole table — tokens, hit rate, cost,
seconds per turn — from a worker log. Put the figure in the closing report: an
overnight run with no cost line is how the next one gets approved without anyone
knowing what it costs. And see `dot/pi/CLAUDE.md` for why these numbers argue for
Pro at `high` rather than Flash.

---

## Hard rules

Everything under `/orchestrate`'s "Hard rules", plus:

- **pi's provider is `deepseek`. Never Claude.** See "Why this split exists".
- **Never let a worker run unsandboxed against a repo you do not trust.** P1c is
  not a formality.
- **Never edit the global permission config** to make a run work. Project scope, in
  the worktree, deleted afterwards. A global `yoloMode` outlives the run and
  silently changes every interactive pi session afterwards.
- **If a worker stalls with no output for a long stretch, read the log before
  killing it.** A blocked permission gate and a long thinking turn look identical
  from outside, and only one of them is fixed by restarting.
