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
/orchestrate-pi --workers 3                     # concurrency (default 2)
/orchestrate-pi --model flash                   # pro (default) | flash
/orchestrate-pi --thinking max                  # off | low* | high (default) | max
```

`low` exists on Flash only — Pro's ring is `off → high → max`. See the model table
in `~/Git/toolbox/dot/pi/CLAUDE.md`.

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
before the run, not after.

---

## Step P2 — Spawning a worker

Write the prompt to a file and pass it with `$(cat …)`. Do not inline it — worker
prompts are Markdown full of backticks and newlines, and shell quoting mangles them
quietly. Same lesson as `gh issue create --body-file`.

```bash
cd /abs/path/to/worktrees/issue-16 && pi \
  --provider deepseek --model deepseek-v4-pro --thinking high \
  --approve \
  --session-id issue-16 \
  --mode json \
  -p "$(cat /abs/path/to/.claude/pi-prompts/issue-16.md)" \
  > /abs/path/to/.claude/pi-logs/issue-16.jsonl 2>&1
```

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

`--session-id` makes the session addressable. To push back on a worker without
re-sending its whole context:

```bash
cd <worktree> && pi --approve --session-id issue-16 --continue \
  -p 'The GUT suite fails on <file>. Fix it and re-run; do not disable the test.'
```

Cheaper than a fresh worker, and it keeps the prior reasoning in context.

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
specific to *this* issue.

Before merging, confirm the worker left no scaffolding: the `.pi/` config from P1b,
stray log files, `--session-id` artifacts.

### Report what it cost

`--mode json` emits usage per turn. Sum `totalTokens` across the run and price it
from the table in `dot/pi/CLAUDE.md` (Pro $0.435/M in, $0.87/M out; Flash $0.14 /
$0.28). Put the figure in the closing report — an overnight run with no cost line
is how the next one gets approved without anyone knowing what it costs.

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
