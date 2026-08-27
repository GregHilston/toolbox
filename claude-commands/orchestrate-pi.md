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
/orchestrate-pi --model pro                     # flash (default) | pro
/orchestrate-pi --thinking max                  # off | low* | high (default) | max
```

`low` exists on Flash only — Pro's ring is `off → high → max`. See the model table
in `~/Git/toolbox/dot/pi/CLAUDE.md`.

### Flash is the default. Escalating to Pro is a decision you have to justify

Measured on one nine-issue run: the same tokens cost **$1.59 on Flash against
$4.87 on Pro**, a uniform 3x on every axis since DeepSeek's 2026-08-16 repricing.
That gap used to be pennies and is now most of a run's bill.

What Pro buys over Flash on a *first pass* is unmeasured, and this workflow is
built so that it should not matter: **every worker's diff goes through an
adversarial Claude review before it is merged**, and in that nine-issue run every
single reviewed issue came back with a material finding — a regression the worker
had just introduced, a missed code path, rows rendered below the fold, a rotation
that never re-snapped. Pro's first pass was never sufficient on its own. The
review runs on the Claude subscription and costs this key nothing, so the cheap
worker is not a cheap outcome.

**Reach for `--model pro` only when the issue is one where a wrong answer is
expensive to detect**, which in this repo means:

- combat tick resolution, effect ordering, or a failing golden — the places where
  a plausible-but-wrong diff passes the suite;
- balance judgment, where the answer is a number nobody can eyeball;
- anything the review agent has already sent back twice, which is evidence the
  first pass is genuinely out of its depth.

Everything else — UI, layout, focus, audio, tests, docs, mechanical edits — is
Flash work. **If you escalate, say so in the closing report and say why**, so the
next run has evidence rather than habit. And if Flash's diffs come back visibly
worse in review, that is the benchmark this repo has wanted and never run: record
it and change the default back.

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
that loop is a small fraction of the worker before it, and has caught things the
green suite did not.

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

### P1d. Check the balance and the clock BEFORE spawning anything

**Run this first. It is the cheapest step in the command, and it is the one that
was missing when a run died halfway through.**

```bash
set -a; . ~/Git/toolbox/nixos/secrets/.env; set +a
deepseek-preflight.py            # exit 0 clear, 1 needs a human, 2 could not tell
```

It answers the two questions that stay invisible until the bill arrives:

**Is there money?** A run that starts under-funded does not fail cleanly. It dies
mid-flight on a `402 Insufficient Balance`, and **pi still emits `agent_settled`,
so `pi-workers.py` reports the worker `done` rather than `dead`.** In the run this
step comes from, three workers were killed that way and reported completion with
turn counts and a cost; all three had zero commits and five modified files sitting
uncommitted. About $1.45 of real spend that produced nothing committable — 30% of
the run. The default floor is $2; raise it with `--min-balance` for a big queue.

**Is it peak?** DeepSeek bills **01:00–04:00 and 06:00–10:00 UTC, Monday–Friday**
at double. Everything else, weekends included, is off-peak. That is only 35 of 168
hours, so this is a trap to avoid rather than a discount to chase — and the trap is
that those windows are **21:00–00:00 Eastern, Sunday through Thursday** (20:00–23:00
in winter). "Kick off an overnight run after dinner" walks straight into the first
window and then into the second before morning, at 2x throughout. The script warns
when a window opens within 90 minutes, because a run started just before one pays
peak for its second half.

If it reports a problem, **tell the user and stop** rather than spending into it.

**On the token floor**, which used to be this step: every tool schema and context
file is re-sent on every request as a cache read, and in `~/Git/gridkeep` that
floor is ~16k tokens. It is not the small number the old note claimed — see
"Report what it cost" — so the arithmetic that matters is turns × context, and the
lever is fewer turns.

### P1e. Set PI_STATUS_FILE, and never diagnose a worker by log size again

Export `PI_STATUS_FILE=<worktree>/.pi/status.json` on every spawn. The
`orchestration-status` extension then rewrites that file on every turn and every
tool call — atomically, so it is always safe to read mid-write:

```json
{ "phase": "tool", "pid": 51035, "turn": 42, "toolCalls": 26,
  "currentTool": "bash", "lastToolBrief": "godot --headless --script tests/run.gd",
  "lastText": "Tests pass. Now updating the docstring.",
  "lastActivityAt": "2026-08-27T16:24:03.114Z",
  "lastBlocked": "bash @ turn 12", "blockedCount": 1,
  "recent": ["▸ bash godot --headless", "» Tests pass. Now updating the docstring."],
  "usage": { "totalTokens": 3562885, "cacheRead": 3453824, "costUsd": 0.0316 } }
```

**This exists because a dead worker and a thinking worker are indistinguishable
from outside.** A worker that dies on spawn writes a 0-byte JSONL; one thinking
hard for four minutes also writes nothing new. In the run this was built from,
two dead workers were reported as "still running" twice before anyone ran `ps`.

Poll every worker at once with `pi-workers.py` (on `$PATH` from `bin/`):

```bash
pi-workers.py --root <repo>            # the table
pi-workers.py --root <repo> --json     # for you
pi-workers.py --root <repo> --strict   # exit 1 if anything needs attention
pi-workers.py --root <repo> --watch    # live, for a human in a second terminal
```

```
worker               state     turn tools     age      cost  doing
issue-95             ▸tool       18    11      3s   $0.0151  bash godot --headless --script tests/run_gut.gd
issue-96             ⏸stalled    42    26    603s   $0.0316  no activity for 603s while phase=thinking
issue-97             ✗dead        5     2      3s   $0.0009  process 51035 is gone — check the log and the branch
issue-98             ∅nostart     -     -       -         -  no status file — it never started
issue-99             ✓done        2     1     38s   $0.0000  » I looked at the directory listing.

Needs attention: issue-96, issue-97, issue-98
```

The five states are the whole product, and three of them are absences that a
human reading a log directory cannot tell apart:

- **`nostart`** — provisioned but no `status.json`. It never started; this is
  the spawn bug in Step P2, not a slow turn. Discovery keys off
  `.pi/status.json` **or** `.pi/guardrails.json`, which is why arming the
  guardrails in P1b-bis is what makes a never-started worker visible at all —
  and why a bare `.pi/` is deliberately not enough (`~/.pi` is pi's own config
  directory, and counting it reported `$HOME` as a dead worker).
- **`dead`** — the recorded `pid` is gone. This is the one that fooled us twice.
  Read the log before respawning.
- **`stalled`** — quiet for longer than `--stall-seconds` (default 120) while
  still claiming to work.
- **`done`** — `settled` or `shutdown`; go verify the branch.
- anything else — the live phase, with `doing` showing the current tool's actual
  command, or the last thing the worker said.

There is a sixth state, `unknown`: a status file that is present but not valid
JSON, or not an object. It also flags for attention. It should not happen —
writes are atomic — so treat it as corruption rather than a torn read.

`lastBlocked` / `blockedCount` count **any failed tool call**, not only
guardrail refusals. A refusal is one — the guardrails block via an error result,
and one extension cannot see another's return value — but so is a failing test
command or an `edit` whose `oldText` did not match. So a rising `blockedCount`
means "this worker is hitting errors", and only the log says which kind. Worth a
look either way; do not read it as "it is fighting the boundaries" without
checking.

**Delete stale status files before the run starts.** Nothing removes
`status.json` on its own, so a worker killed in a previous run leaves a
non-terminal phase with a dead pid behind forever. The next run then opens with
a permanent `⚠1 dead`, `--strict` never exits 0 again, and the status-line row
never clears — a false alarm that trains you to ignore the real one:

```bash
rm -f <repo>/worktrees/*/.pi/status.json
```

Do this once in P1, after the worktrees exist and before the first spawn.

It also retires log-scraping for telemetry: `usage` here is the running total, so
`.claude/pi-usage.py` becomes a cross-check rather than the only source.

**A `dead` worker has not necessarily failed.** The state means the process is
gone while the last published phase was non-terminal, and pi only publishes a
terminal phase from `agent_settled` / `session_shutdown`. A worker that finished
its work and then died — a crash on exit, a `SIGKILL`, a provider abort — lands
here too. Read the log and the branch before concluding the work was lost.

**The same file drives the status line.** `pi-workers.py --from-statusline
--oneline` is wired into ccstatusline as a third row, so the user sees
`pi 5w 2▸ 1~ 1✓ $0.0912 ⚠1 stalled` at a glance for the whole run, without
asking you and without spending a token. It renders nothing when no workers
exist, so the row is invisible outside a run.

---

## Step P2 — Spawning a worker

Write the prompt to a file and pass it with `$(cat …)`. Do not inline it — worker
prompts are Markdown full of backticks and newlines, and shell quoting mangles them
quietly. Same lesson as `gh issue create --body-file`.

```bash
set -o pipefail
cd /abs/path/to/worktrees/issue-16 && \
  PI_STATUS_FILE=/abs/path/to/worktrees/issue-16/.pi/status.json pi \
  --provider deepseek --model deepseek-v4-flash --thinking high \
  --approve \
  --session-id issue-16 \
  --mode json \
  -p "$(cat /abs/path/to/.claude/pi-prompts/issue-16.md)" 2>&1 \
  | pi-narrate.py --label issue-16 \
      --raw /abs/path/to/.claude/pi-logs/issue-16.jsonl \
      --alerts /abs/path/to/.claude/pi-logs/alerts.log
```

### Never redirect the whole stream to a file

**`> issue-16.jsonl 2>&1` is what made every worker a black box, and it was our
own doing.** Claude Code captures a background command's output from a PTY, so a
full redirect means the harness sees zero bytes and the task row reads *"no
output available"* for the entire run. The information was never missing — pi
emits a rich, line-buffered event stream in `--mode json`. We were throwing it
away and then reading a 13MB log back with `jq` to recover a fraction of it.

`pi-narrate.py` sits in the pipe instead. It writes the untouched JSONL to
`--raw` itself (so no `tee`), and emits one compact line per thing that
happened:

```
issue-16 t42   6m12s ▸ bash godot --headless --script tests/run_gut.gd
issue-16 t42   6m55s ✓ bash ok (43s)
issue-16 t43   6m56s » Tests pass. Now updating the docstring.
issue-16 t44   7m02s ✗ edit FAILED after 0s: no match for oldText in src/foo.gd
issue-16 t50   9m10s · 50 turns, 31 tools, $0.0212
```

The harness shows the most recent line as the task's status, so four workers
become four live rows; `Read` the task's output file for the whole narration at
any point. Three details that matter:

- **`set -o pipefail`**, or the shell reports the narrator's exit status and
  pi's failure disappears.
- **`2>&1` before the pipe.** pi's stderr — the settings-lock warning, provider
  errors — used to vanish into the log. The narrator surfaces non-JSON lines
  with a `!` prefix rather than dropping them.
- **`--alerts` should be one shared file for the whole run**, not one per
  worker. Step P2-bis watches it, and `tail -F` over a glob only picks up files
  that already exist.

Thinking is *not* narrated by default — it is long and mostly restates the task.
`--thinking` turns it on when a worker is behaving strangely and you want to see
why.

**Write the prompt file in a separate, earlier call.** A heredoc and a backgrounded
`pi` in one command silently produces nothing: the file is written, the harness
reports the command as running, no process ever starts, and the redirect target sits
at 0 bytes with no completion notification. It is indistinguishable from a long
turn, and it cost two stalled workers in one run. One call writes the file; the next
call is a bare `pi` invocation and nothing else.

Run it with `run_in_background: true` — you are re-invoked when it exits, which is
what keeps worker slots rotating. Absolute paths everywhere; the Bash cwd persists
between calls and `/orchestrate`'s Step 2a-bis catalogues what that has already cost.

---

## Step P2-bis — Arm one monitor for the whole run

After the first worker is up, start a single `Monitor` on the shared alerts file:

```
Monitor(command: "tail -n +1 -F /abs/path/to/.claude/pi-logs/alerts.log",
        description: "pi worker failures, blocks and completions",
        persistent: true)
```

Each line becomes a chat notification, so a guardrail block or a dead worker
interrupts you and the user rather than waiting to be discovered on the next
poll.

**Watch the alerts file, never the narration.** The narration is ~150 lines per
worker; a monitor fed that gets rate-limited and auto-stopped, and you lose the
alerting entirely. `pi-narrate.py` already makes the split: only tool failures,
guardrail blocks, retries, compaction, orchestrator interventions and
completion reach `--alerts`.

Create the file before arming the monitor (`mkdir -p` its directory and
`touch` it), or `tail -F` spends the run waiting for a path that the first
worker has not written yet.

**The prompt is `/orchestrate`'s Step 4 prompt, unchanged**, minus the parts that
assume a subagent. Keep every one of: the verbatim issue body, "check whether it
already shipped", the `Closes #N` trailer instruction, the decisions-it-must-make-
alone list, never-push/never-merge/never-`gh`-write, the named forbidden interactive
scripts, and the other agents' issue numbers.

Three additions specific to pi:

- **State the model and that thinking is on.** A worker that does not know it has a
  thinking budget will not use it. Say `deepseek-v4-flash` when that is what it
  is — a prompt that claims Pro while Flash is running is a small lie that makes
  the transcript useless as evidence for the Flash-versus-Pro question.
- **Ask for the final report as the last message**, in the shape Step 4 requires.
  There is no return value here — you read it out of the log.
- **Forbid `/login`, `pi install`, and any edit to `~/.pi`.** A worker has no reason
  to touch pi's own configuration, and one that does can change the next worker's
  behaviour.
- **Tell it to commit each atomic change as it goes green, not to batch them.** A
  pi worker can be killed mid-run by something that is nobody's fault — a 402, a
  provider abort — and it keeps only what it committed. Three workers in one run
  lost everything they had done this way, and the loss is invisible until you look
  at `git log` rather than at the completion event.

### A pi worker cannot see, and will try anyway — say so in the prompt

`pi --list-models deepseek` reports **`images: no`** for both `deepseek-v4-pro`
and `deepseek-v4-flash`. That is a hard capability fact, not a preference: the
model cannot be shown a PNG. Only `deepseek-v4-flash-vision-exp` can, and it is
not what these runs use.

**Left unsaid, a worker will try to read the image anyway**, and it is expensive.
In one run a worker faced a screenshot diff it could not explain and spent about
eight turns on `python -c "from PIL import Image"` (not installed), then
`magick ... txt:-` piped through `awk` over a per-pixel colour dump, trying to
reconstruct a 1280x720 image from statistics. It concluded "nearly identical
statistics but every pixel differs", which is true and useless. The orchestrator
opened the file and read the answer in one glance: the worker's new HUD control
had overflowed the top bar and was clipped mid-word, pushing the whole layout
sideways.

So put this in every prompt, in these words:

- **Never try to read an image.** No PIL, no ImageMagick, no `txt:` pixel dumps,
  no `awk` over colour maps, no compare/statistics arithmetic. You cannot see it
  and the numbers will not tell you what a glance would.
- **`DIFF.md` is text and you *can* read it.** Percentages, bounding boxes and
  shot names are yours. Use them to decide *which* shots matter.
- **When a percentage confuses you, stop and say so.** Name the shot, say what you
  changed and what you expected to move, and hand it to the orchestrator. That is
  a finished piece of work, not a failure.
- **Never assert what a screenshot shows.** Say what you *predict* and mark it
  unverified. In the same run another worker's report described "a green +1 food
  and an orange -1 food stacked, each on a dark rounded plate" in a shot that
  contained **no popups at all** — it described what the code should produce and
  offered it as evidence the issue was fixed. Write "I expect X; I cannot confirm
  it", and the orchestrator will confirm or correct it.

The division of labour is: **the worker produces the evidence and names what to
look at; the orchestrator looks and says what is there.** That is the whole reason
this command pairs a blind implementer with a sighted reviewer, and it only works
if the worker does not try to do both halves.

### pi's bash tool times out at 180s — so some things you ask for cannot be done

A worker's `bash` call is killed at three minutes. Two consequences bite in this
repo, and both look like the worker failing rather than the instruction being
impossible:

- **A full `./run_ui_screenshots.sh --sweep` (289 shots) exceeds it.** Asking a
  worker to "check it across the sweep" is asking for something it cannot run in
  one call. Either scope the capture (`--only=<group>`, or `--sizes=1024x640` for
  the one resolution that matters), or **run the sweep yourself** and hand back
  the `DIFF.md` — the orchestrator has no such limit.
- **A headless Godot probe that never calls `get_tree().quit()` runs forever**
  and eats the whole three minutes. If you tell a worker to measure something with
  `godot --headless -s probe.gd`, tell it to quit at the end.

The full GUT suite (~50s) and pytest with coverage (~110s) both fit, but a commit
touching both runs them back to back through the hook and lands near three
minutes — so a *commit* can time out even though each suite would not. Warn the
worker that a hook-driven timeout is not a test failure, and that re-running the
commit is safe.

**Scratch files a probe leaves behind are the worker's to clean up.** Say so: a
`probe_*.gd` at the repo root is not part of the change and must not reach the
diff.

### Do not change model mid-session — it collapses the cache

`--continue` resumes a warm session, but **the cache is keyed on the model.**
Resuming a Pro session with `--model deepseek-v4-flash` re-sends the entire
context as fresh input: measured on a resumed worker, turn 2 showed a **1% cache
hit rate and a $0.049 cold read** of its ~200k context, against the ~99% it had
been running at.

It still paid off there — Flash's cheaper rate earns the one cold read back within
a few turns — but decide the model **before** the first spawn and keep it. Prompt
caches match on an exact prefix from the first token, so anything that perturbs
the prefix costs a full re-read.

The same rule applies to the prompt itself: **keep it byte-stable across turns and
put anything variable at the end.** Never inject a timestamp, a run id or a
worker count near the top of a worker prompt.

### `--only=<group>` makes the diff look catastrophic, and it is an artifact

`./run_ui_screenshots.sh --only=combat` regenerates *only* the combat shots into
`out/`, while `baseline/` still holds all 289. The differ then reports every shot
it did not capture as `_removed_`. That is not a signal and it has cost a worker
four turns.

Either run the full capture so both sides hold the same set, or keep `--only` and
read just the rows for the shots actually captured. **A grep that returns nothing
after filtering out `_removed_` is the good outcome.** Put this in the prompt of
any worker doing UI work.

### Steering a worker that is still running

`-p` is a closed box: everything you learn from the narration while a worker
works is unusable until it finishes. `pi-rpc.py` closes that gap by driving the
same agent over pi's RPC protocol, which accepts a message mid-flight.

Spawn it exactly as above, with `pi-rpc.py run` in place of the `pi | narrate`
pipeline:

```bash
PI_STATUS_FILE=/abs/path/to/worktrees/issue-16/.pi/status.json \
pi-rpc.py run --dir /abs/path/to/worktrees/issue-16 --label issue-16 \
  --prompt-file /abs/path/to/.claude/pi-prompts/issue-16.md \
  --raw /abs/path/to/.claude/pi-logs/issue-16.jsonl \
  --alerts /abs/path/to/.claude/pi-logs/alerts.log \
  -- --provider deepseek --model deepseek-v4-flash --thinking high --approve
```

Narration and lifecycle are identical — it still runs backgrounded, still exits
on `agent_settled`, still notifies you on completion. That is deliberate: a
supervisor that outlived its work would trade the completion notification for
the steering, and the notification is what keeps worker slots rotating. What you
gain is a control socket:

```bash
pi-rpc.py state --dir <worktree>                      # is it streaming? how many messages?
pi-rpc.py steer --dir <worktree> 'You are editing the wrong file; see src/foo.gd'
pi-rpc.py follow-up --dir <worktree> 'When done, also update the CHANGELOG'
pi-rpc.py abort --dir <worktree>                      # cleanly, rather than kill(1)
```

`steer` lands after the current tool calls finish and before the next model
call, so it redirects the worker without corrupting a half-finished turn.
Measured: a worker three steps into a four-step task abandoned the remainder and
complied on the next turn. `follow-up` waits for it to finish instead.

**Steer on evidence, not on nerves.** The narration is now detailed enough to
watch a worker think, and the temptation is to intervene on the first line that
looks wrong. A worker that is mid-exploration often looks lost and is not. Steer
when the *narration shows a fact you have and it does not* — the wrong file, an
issue it has misread, a script you know hangs. Otherwise let it finish and use
the review loop, which is cheaper and has a better record.

Every intervention is written into the narration and the alerts file, so a diff
that changed direction mid-run has the reason recorded beside it.

### Iterating with a finished worker

To push back on a worker after it has settled, without re-sending its context:

```bash
cd <worktree> && pi --approve --continue \
  -p 'The GUT suite fails on <file>. Fix it and re-run; do not disable the test.'
```

**A resumed worker cannot be steered.** `pi-rpc.py run` opens a control socket;
a bare `pi --continue` does not, so `pi-rpc.py steer` has nothing to talk to and
the only intervention left is kill-and-`--continue`. That is survivable — the
session and the working tree both persist — but it costs a turn and loses the
in-flight reasoning. **If you expect to intervene, resume through `pi-rpc.py run`
rather than a bare `--continue`.**

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

**You can now watch the worker, but watching is not verifying.** The narration
in Step P2 gives you what a subagent's transcript would: what it said, what it
ran, what failed. That is a real improvement over the JSONL-and-a-final-message
this command used to describe — but it is still the worker's account of its own
work. Treat the report as a claim and let the diff be the evidence; read it
yourself. Spot-checking the highest-consequence claim stops being good practice
and becomes the load-bearing step. A convincing narration makes this *easier to
skip*, which is the new failure mode to watch for in yourself.

**Review with a Claude subagent, not another pi.** One adversarial review of
`git diff main...HEAD` is a single cheap read where judgement matters most, and it
is the right place to spend Claude tokens in a design whose whole point is spending
them sparingly. Give it the worktree path, the sandbox rule, and the failure modes
specific to *this* issue — generic "review this" gets generic results.

### Closing the review loop — same loop, different resume mechanism

**`/orchestrate`'s "Always close the review loop back to the original agent" owns
this**, including why the reviewer must be fresh, why the findings go back to the
*original* worker, why it is framed as a decision rather than a work order, and
what it has caught. Read it there; none of that changes because the worker is pi.

Two things are specific here:

- **You resume the worker with `pi --continue`, not `SendMessage`.** From the
  worktree's own cwd, with no `--session-id` (pi refuses the pair). See "Iterating
  with a finished worker" above.
- **It is very nearly free, which is worth knowing before you consider skipping
  it.** `--continue` resumes a warm session, so billed input collapses — measured
  at a **99.4-99.8% cache hit rate**, with one feedback pass billing 3,993 fresh
  input tokens against 44,113 for the worker that preceded it. A feedback round is
  a small fraction of the worker it corrects.

Before merging, confirm the worker left no scaffolding: the `.pi/` config from P1b,
stray log files, `--session-id` artifacts. `pi-rpc.py` removes its own `.pi/rpc.json`
and socket on exit, but a worker killed with `SIGKILL` cannot — a leftover
`rpc.json` is a hint that something ended badly, not a file to commit.

### Report what it cost — and do not trust pi's own number

`--mode json` emits usage per turn, on `message_end` events — sum those, not
`turn_end`/`agent_end`, which repeat the same numbers.

**pi's `cost` object is stale and under-reports by about 3x.** DeepSeek repriced
at 16:00 UTC on 2026-08-16 and introduced peak/off-peak rates; pi 0.84.3's
built-in catalog predates that. The worst error is on cache hits, which it prices
at a sixth of the truth — and cache reads are half the bill on a long run, so the
error compounds exactly where the spend is. An earlier version of this file
repeated the catalog's numbers as fact. They were, until they weren't.

Use `gridkeep/.claude/pi-usage.py`, which prices each turn from the official table
at the rate in force when that turn ran and prints both numbers, so the gap stays
visible. `pi-workers.py` shows the same corrected figure live, plus a cache-hit
column.

Measured over one nine-issue run on **Pro at `high`**, four workers rolling:

| | pi reported | real, off-peak |
| --- | ---: | ---: |
| fresh input (1.05M) | | $0.69 |
| **cache read (111.4M)** | | **$2.45** |
| output (871k, 81% thinking) | | $1.73 |
| **total** | **$1.62** | **$4.87** |

Where those tokens go, measured on the same run: **24% were spent before the
worker's first edit**, and context grew **9-15x** over a worker's life (~20k on
turn one, 175-295k at the end). `/orchestrate`'s "Write the prompt to remove
turns, not to add context" and its scout-once step are the levers for both, and
they are shared rather than pi-specific — but this is where the meter is, so it is
worth knowing the numbers here.

Three things follow, and they invert the advice that used to be here:

- **Cache reads are half the bill, so turn count is the lever.** 111M cache reads
  over ~750 worker turns is ~148k re-sent every turn, growing as the session
  lengthens — cost is roughly *quadratic* in turns. The old note said "the longest
  runs are the cheapest per token"; that was an artefact of the 6x cache-price
  error. Trim the prompt, and pre-digest what a worker would otherwise spend turns
  discovering.
- **Prefer Flash for the first pass.** Uniformly 3x cheaper now; the same tokens
  cost $1.59 instead of $4.87. Every reviewed issue in that run came back with a
  material finding, so Pro's first pass was never sufficient on its own — what it
  buys *ahead of a review* is unmeasured, and the review runs on the Claude
  subscription and costs this key nothing.
- **Thinking is ~29% of spend** (703k of 871k output tokens were reasoning). Buy it
  where a wrong answer costs a debugging cycle, not by default. Flash has a `low`
  rung Pro lacks.

Put the real figure in the closing report. An overnight run with no cost line is
how the next one gets approved without anyone knowing what it costs.

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
  from outside, and only one of them is fixed by restarting. `pi-workers.py`
  separates them now — `stalled` versus `dead` versus `nostart` — but it tells
  you *which* question to ask, not the answer.
- **Never redirect a worker's stdout to a file.** That is what made every run a
  black box; pipe it through `pi-narrate.py` instead, which writes the raw log
  itself. See Step P2.
- **The monitor watches the alerts file, never the narration.** A monitor fed
  the full stream is rate-limited and stopped, and then nothing alerts at all.
