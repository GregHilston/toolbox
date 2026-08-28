# Orchestrate GitHub Issues

Drive a set of GitHub issues to completion by spawning one subagent per issue,
each in its own git worktree, while you act as orchestrator: you merge, you own
every `gh` write, and you never stop until the queue is drained or the user says
so.

**You are the orchestrator. You do not implement issues yourself.** Your job is
preflight, spawning, verifying, merging, and bookkeeping.

## Usage

```
/orchestrate 16 23 41                                  # these issues, in this order
/orchestrate https://github.com/owner/repo/issues/16   # URLs work too
/orchestrate --label prep:ready                        # everything /prep marked ready
/orchestrate --workers 4                               # concurrency (default 2)
/orchestrate --max 4                                   # stop after 4 issues (usage-limit friendly)
/orchestrate --model opus                              # sonnet (default) | opus | haiku
```

Numbers, `#16`, and full URLs are all accepted. With no issues named, default to
`--label prep:ready` rather than to every open issue — picking up an unprepped
backlog wholesale is the main way an overnight run is wasted.

### This command and `/orchestrate-pi` are the same job, two engines

`/orchestrate-pi` runs the *implementation* on local `pi` processes talking to
DeepSeek, billed to a metered key, while you stay the orchestrator. Everything
else — issue selection, the worktree preflight, queue planning, the review loop,
merge verification, `Closes #N` trailers, filing agent findings, the closing
report — is meant to be **identical**, and that file says so: it covers only what
differs and defers here for the rest.

So a change to the shared half belongs *here*, and `/orchestrate-pi` inherits it.
Only put something there if it is genuinely about pi: the balance and peak-hour
preflight, the status file, the guardrails, `--continue` instead of SendMessage.
Two copies of the shared half would drift within a month.

## `gh` and the sandbox

Every `gh` call needs `dangerouslyDisableSandbox: true`. Sandboxed, the filtering
proxy intercepts TLS and `gh` refuses the certificate:

```
Post "https://api.github.com/graphql": tls: failed to verify certificate: x509: OSStatus -26276
```

That error is the sandbox — not the network, not the token. **`gh auth status`
fails the same way and misreports it as an invalid token.** Establish this once
in preflight, and put it in the agent prompt as settled fact.

---

## Step 0 — Have these issues been prepped?

```bash
gh issue list --state open --limit 200 --json number,title,labels,body
```

`/prep` researches each issue, gets the user's answers, rewrites the body into a
real spec, and labels it `prep:ready` or `prep:blocked` with a `size:`.

- **Labelled** — spawn only for `prep:ready`. **Never pick up a `prep:blocked`
  one**; it is blocked because the user has not answered something only they can
  answer, and an agent given it overnight will invent an answer. Use `size:` to
  order the queue and to warn about total cost.
- **An issue carrying both labels** is a `/prep` bug, not a decision. Treat it as
  blocked and say so.
- **Unlabelled** — say so, and offer to run `/prep` first. If the user would
  rather go straight to work, do your own lighter triage before spawning: drop
  anything with no implementable spec (question 2 below), and check each
  remaining issue for whether it has already shipped.

An unprepped queue is the main source of wasted overnight runs. In one real run
three of eight items turned out to be stale or misdescribed, and one contained
two sentences contradicting each other.

---

## Step 1 — Ask before you begin

Ask these with `AskUserQuestion` in ONE call. They change what you do, and the
user is usually about to walk away, so getting them wrong costs the whole run.

1. **Model.** **Default to `sonnet` for the workers and `opus` for the review
   agents**, and ask only whether the user wants to override that. The split is
   deliberate and mirrors `/orchestrate-pi`: the cheap model does the
   implementation, the expensive one does the judging, because the review is
   where defects are actually caught. On a nine-issue run of gridkeep *every*
   reviewed issue came back with a material finding — a regression the worker had
   just introduced, a missed code path, rows rendered below the fold — so the
   first pass being cheaper costs less than it looks, and the review being good
   matters more than it looks.

   Escalate the workers to `opus` for issues where a wrong answer is expensive to
   *detect* rather than merely wrong: anything touching combat tick resolution,
   effect ordering, a failing golden, or balance judgment, where a
   plausible-but-wrong diff passes the suite. Say which issues you escalated and
   why, in the closing report.

   The Agent tool takes `model` (family only: `opus`, `sonnet`, `haiku`, `fable`)
   and has **no effort parameter** — per-agent effort exists only inside a
   `Workflow` script. You cannot pin a point release like "Opus 4.8". Say so
   plainly rather than pretending you can.
2. **Items with no implementable spec.** If you are running unprepped issues,
   some will be one vague line, or will say outright that they are the user's
   design call. Offer: design-doc-only / full autonomous implementation / skip.
   Never silently build a large feature on a guess.
3. **Push policy.** Default to *not* pushing. Check for a pre-push hook first —
   many repos deploy on push, and deploying at 3am can drop live users. **Say
   what this means for the issues** (see "Closing issues" below): unpushed work
   leaves every issue open until the user pushes.
4. **Failure policy.** Default: park the branch unmerged, note it, keep going.
5. **Worker count**, if not given. Default 2. More than ~4 rarely pays: merges
   serialize through you, and unrelated issues get scarce fast in a small repo.
6. **Sandbox** — only after the preflight below tells you the answer.

Also tell the user up front which issues you expect **not** to finish, so "the
backlog will be empty by morning" is never an implied promise you can't keep.

---

## Step 2 — Preflight (do this before spawning anything)

Every minute here saves an agent an hour of confusion. Run the probes, then bake
the answers into the agent prompt template.

### 2a. Where can worktrees live?

The documented `../repo-<name>` convention **often fails**, because the Bash
sandbox typically allows writes only within the repo. Probe it:

```bash
mkdir -p ../probe-xyz && echo ok > ../probe-xyz/x && rm -rf ../probe-xyz
```

If that is `Operation not permitted`, put worktrees **inside** the repo at
`worktrees/<name>` and add `worktrees/` to `.gitignore` as your first commit.

### 2a-bis. Create every worktree with an ABSOLUTE path

The Bash tool's cwd **persists between calls**, so `git worktree add
worktrees/<name>` creates the worktree relative to wherever your shell happens to
be — not the repo root. In one real run this silently produced
`godot-client/worktrees/<name>`, a full nested copy of the repo inside the client
project directory. It was gitignored, so nothing complained, and the agent
working in it only mentioned the odd path in its final report.

Write `git worktree add /abs/path/to/repo/worktrees/<name> -b <branch>` every
time, and re-read `git worktree list` after creating one — the printed paths are
the check.

The same trap has three other faces during a run, and all three fail *silently*
rather than loudly:

- **`git merge <branch>` run from inside that branch's own worktree** reports
  "Already up to date" and merges nothing. If a merge you expected to do work
  reports that, check `pwd` and `git rev-parse --abbrev-ref HEAD` before
  believing the branch was already in.
- **`git status --porcelain <path>`** with a path that does not resolve from cwd
  warns on stderr and **exits 0 with no output** — so
  `git status --porcelain tests/goldens/ && echo "REGEN IS A NO-OP"` cheerfully
  prints the success message for a directory it never looked at. Verification
  commands are the worst possible place for this, because the failure mode is a
  false pass on exactly the check you added to be careful.
- **Any script or file read** failing with `can't open file`, which reads as "the
  file is missing" and is actually "you are in the wrong directory".

Treat any error naming a path with a doubled or missing prefix as a cwd problem
first. Cheapest durable fix: prefix every orchestration command with
`cd /abs/path/to/repo &&`, and never rely on where the last call left you.

### 2b. Does a worktree checkout even work sandboxed?

```bash
git worktree add worktrees/probe -b probe
```

This commonly fails with `Operation not permitted` on tracked files under
`.claude/`, `.mcp.json`, `.vscode/`, plus `could not lock config file
.git/config` — the sandbox denies those paths, and git must write every tracked
file. If so, **worktree add/remove must run with `dangerouslyDisableSandbox:
true`**, and you should do it yourself rather than delegating it.

### 2c. Can an agent run the test suite and commit?

Make a trivial commit in the probe worktree, letting hooks run. Watch for a
package manager failing on its cache (`uv` → `~/.cache/uv`, also npm/pnpm/cargo).
If the toolchain cannot write its cache, **every** test run and commit fails, and
agents must run unsandboxed. This is the single most important thing to discover
before spawning, and it is invisible until something tries to run.

### 2d. Baseline the suites, and time them

Run every suite on a clean tree and record pass counts. You need this to tell an
agent's regression from a pre-existing failure, and the timings tell agents how
patient to be per commit (say so in the prompt — an agent that thinks a 90s hook
has hung will start using `--no-verify`).

### 2e. Inventory the traps

- **Interactive scripts.** Anything that waits on typed input hangs an unattended
  agent forever. Grep for `read -p`, `input(`, confirmation prompts. Name them in
  the prompt as forbidden, and name the non-interactive equivalent.
- **Hooks.** What do pre-commit and pre-push actually run?
- **Generated/derived files.** Goldens, snapshots, lockfiles, generated themes.
  Note the regeneration command — you will need it at merge time.
- **Gitignored test baselines** (e.g. screenshot baselines). If they are not
  committed, each agent must build its own before/after, and a diff against your
  baseline is meaningless.
- **Gitignored databases and other untracked local state.** *Check this
  explicitly — a worktree does not inherit it, and both possible mistakes are
  silent.* If the repo's dev database is gitignored (`*.db` catches it and nobody
  remembers), then **a fresh worktree has no database at all**. An agent told
  "the database is shared, read it read-only" will find nothing where you said it
  would; an agent told nothing will quietly create an empty one, derive numbers
  from zero rows, and report a confidently wrong answer. Establish which it is
  with `git check-ignore -v <path>` plus an `ls` in a probe worktree, and give
  every agent that needs real data the **absolute path in the primary checkout**
  along with a read-only access recipe (`sqlite3 'file:/abs/path?mode=ro'`, or
  `sqlite3.connect('file:...?mode=ro', uri=True)`). Say plainly that this one
  file is the sole exception to "never touch the primary checkout" — otherwise a
  careful agent will refuse to read it and guess instead.

  The corollary reshapes the queue: **untracked-and-gitignored state is per
  worktree, so it is not a scheduling constraint.** An issue that says "this and
  #23 both use the database, serialize them" is reasoning about the
  single-checkout world. Two agents each running their own migrations and test
  fixtures collide on nothing. Only *reads of the primary checkout's* copy
  serialize — and then only against something that would rewrite that copy, which
  no agent should be doing anyway. Same logic as the screenshot baselines above,
  and worth re-deriving per repo rather than trusting an issue's own scheduling
  notes.

**Tear the probe down completely** and confirm `git status` is clean before
proceeding.

---

## Step 3 — Plan the queue

- **Merge coupled issues into one agent.** If issue A names B as a prerequisite,
  or GitHub's blocked-by field links them, or they want the same
  regeneration/verification pass, they are one unit. Two agents cannot share a
  dependency. One agent may own several issues; its commits then carry several
  `Closes #N` lines.
- **Serialize issues that touch the same subsystem.** Two agents editing the same
  screen or module will conflict at merge. Sequence them; parallelize across
  unrelated areas.
- **Start the largest issue first** so it has the most wall-clock.
- **Run rolling, not in batches.** Refill a slot the moment one finishes rather
  than waiting for the whole cohort. Strict batches waste hours when a 10-minute
  issue is paired with a 3-hour one. With `--workers N`, the invariant is: while
  the queue is non-empty, N agents are in flight.

### Plan each issue before you spawn it — the highest-leverage step in the command

**The ticket says what and why. The plan says where and how, and you write it
fresh, at spawn time, against current HEAD.** That split is the whole design:
`/prep` produces something durable that a human argues with, and this produces
something perishable that an agent executes.

Why it is worth a step of its own, measured on a nine-issue run: **24% of all
tokens were spent before the worker's first edit**, and workers explored between
**12 and 49 turns** each — even though every prompt already carried a "Where to
look" list of the right files. **File paths alone do not stop exploration.** They
tell an agent where to start reading, and everything it reads then sits in its
context for the rest of the session.

#### Produce it with one `Plan` agent per issue

Spawn a `Plan` subagent (or do it yourself for a repo you know cold), given the
issue body and the worktree. Ask it for **at most ~2k tokens**, because whatever
it writes rides along on every turn of that worker — a bloated plan is worse than
none. See "Write the prompt to remove turns" for the break-even.

It should return:

- **Exact anchors: `path:line-range`, verified against HEAD right now.** This is
  the half `/prep` deliberately does not write, because line numbers rot between
  prepping and running.
- **The two or three facts that make reading unnecessary** — "`focus_first()` is
  defined here and called nowhere", "`_remembered_focus` is only ever assigned in
  `build()`, which runs before any button exists".
- **What is already ruled out**, so it is not re-derived.
- **The shape of the change**, not the code. Where the seam is; which file owns
  the fix. Not a diff — a worker handed a diff stops thinking.

#### Give the planner this checklist

These are drawn from what adversarial review actually caught after the fact.
Roughly half of a run's findings are things a planner could have surfaced first,
and they cluster:

- **Does the asset exist?** A glyph, an icon, a font codepoint, a sound. One
  branch shipped `⏸` as its only mouse affordance; the codepoint is not in the
  project's font at all and was being drawn by whatever the host OS supplied.
  Check the actual file, not the block it belongs to — coverage is per codepoint.
- **Who else handles this input, and in which handler?** Binding a key is not
  local. One branch bound `P` and silently broke typing the letter "p" in the
  bug-report field, because that screen handles the action in `_input` — ahead of
  the GUI — deliberately, to protect the player's paragraph.
- **What is the render and clip chain?** A control that draws correctly can still
  be invisible. One branch's popups rendered perfectly at 79% alpha and were
  clipped entirely by an ancestor's `clip_contents`.
- **Who are all the callers?** A fix wired to one entry point leaves the others.
- **What happens at the minimum window?** Read it from the project settings, not
  from the design size.

#### One shared map when the queue overlaps

If several issues touch the same subsystem, hoist the common half into one map
included in every prompt — rediscovery is paid per worker, a map is written once.
Skip it when the issues share nothing; then it is pure overhead.

#### Tell the worker the plan is evidence, not scripture

Include this in the prompt: *the anchors were verified at spawn, but the file may
have moved; if a line number is wrong, say so and continue from what you can
actually see.* A worker that trusts a stale anchor over the file in front of it is
a worse failure than one that explores.

#### Measure whether it worked

Record turns-before-first-edit per worker and compare against the run that
motivated this: **24% of tokens pre-edit, 12–49 turns**. If planning does not move
that, it is costing you a step and buying nothing — and you will only know if you
wrote the number down.

**Planning does not replace the review loop, and must not be sold as doing so.**
On the run above, about half the findings were things no plan could have seen —
a regression introduced by the fix itself, a rotation path that never re-snapped,
a container that traded a horizontal overflow for a vertical one, four rows added
below the fold. Those do not exist until the code does. Planning halves the
exploration and some of the defects; review catches the rest.

Write the queue into a state file (`.claude/orchestrate-state.md`, gitignored) —
issue number, branch, status, notes. If your context is compacted mid-run, this
is the only thing that lets you pick up cleanly. Update it at every transition.
The issue labels are *not* a substitute: they say what `/prep` decided, not where
this run has got to.

Optionally mark what is in flight so a second session does not double-book:
`gh issue edit N --add-label in-progress`. Remove it when the branch merges or is
parked. Skip this if the user is the only one running anything.

---

## Step 4 — The agent prompt

Spawn with the Agent tool, `subagent_type: "general-purpose"`, the agreed model.
**Create the worktree yourself first** so you control the branch name. Name
branches after the issue: `issue-16-storage-click`.

Every prompt must contain:

**Working directory.** The absolute worktree path, its branch, and the commit it
branched from. Plus: never edit the primary checkout, never touch a sibling
worktree.

**The sandbox rule, stated as settled fact** with the reason, so the agent does
not spend twenty tool calls rediscovering it.

**The issue body, quoted verbatim in the prompt.** Paste it; do not tell the
agent to go fetch it. `gh` needs the sandbox off, an agent that has to discover
that burns tool calls on it, and a pasted body cannot change underneath the run.
Give the number and title too, since the commit message needs them.

**Check whether it already shipped.** *This is the highest-value instruction in
the whole command.* Backlogs are pruned less often than they are appended to. In
one real run, **three of eight items were stale or misdescribed** — two features
had already shipped (one three days earlier, one six months earlier) and a third
pointed at the wrong screen. Tell the agent to establish what exists via
`git log` **before** writing code, and to report "stale / partly done / genuinely
missing" as the first line of its report. If you found evidence of prior work
during preflight, hand it over.

**The commit trailer.** The last paragraph of the final commit message for an
issue must be `Closes #16`. One keyword per issue — `Closes #16, closes #17`
closes both, `Closes #16, #17` closes only the first. Tell the agent this
verbatim; it is the whole bookkeeping mechanism and it is easy to get subtly
wrong.

**Keep the prompt's prefix byte-stable, and put anything variable at the end.**
Prompt caches match an exact prefix from the very first token, so a single changed
token near the top invalidates the whole cache for that turn. Never inject a
timestamp, a run id, a worker count or a "you are agent 3 of 5" line near the
beginning of a worker prompt. Order it stable-to-variable: standing rules and
repo facts first, the issue body and anything run-specific last. And **verify hits
by reading the numbers rather than assuming** — `pi-workers.py` shows a cache-hit
column for exactly this reason.

**Write the prompt to remove turns, not to add context.** This is worth its own
paragraph because the obvious move is wrong.

Measured over one nine-issue run: **24% of all tokens were spent before the
worker's first edit** — pure exploration — and context grew **9-15x** over a
worker's life, from ~20k on turn one to 175-295k at the end. Since every turn
re-sends the whole context, cost is roughly *turns x average context*, and both
halves of that product are things the prompt controls.

The trap: **anything you add to the prompt is re-sent every turn.** A 5k-token
briefing across 100 turns is 500k extra cache-reads per worker. So a pack of
pre-digested context only pays if it **removes more turns than it adds context** —
roughly break-even at five exploration turns saved, a clear win past twenty.

So do not paste files in. Paste *coordinates and conclusions*:

- **Exact paths with line ranges**, not just filenames. In that run every prompt
  already carried a "Where to look" list of the right files, and workers still
  explored for 12 to 49 turns before their first edit. Paths alone are not enough
  to stop someone reading the file to find out where the thing is.
- **The two or three facts that make reading unnecessary** — "`focus_first()` is
  defined at `menu_button_row.gd:82` and called nowhere", "`_remembered_focus` is
  assigned only in `build()`". A sentence you already know saves a worker a
  read-and-scan cycle whose file then sits in its context forever.
- **What you already ruled out**, so it is not re-derived.

Keep the whole addition under ~2k tokens. If it is bigger than that, it is a file
paste wearing a disguise.

**The decisions it must make alone**, named explicitly, with "take the
conservative option and flag it in your report." Nobody is awake; an agent that
stalls on a design question wastes the whole slot. If the body is detailed, say
"this is a decision already made, follow it; if you believe it is wrong, say so
loudly rather than silently substituting your own."

**Standing rules:**
- Conventional atomic commits; docs and tests updated *in the same commit* as the
  change they describe. **Commit each one as it goes green rather than batching
  them to the end** — an agent that dies mid-run keeps only what it committed, and
  in one `/orchestrate-pi` run three workers were killed by a provider error and
  lost everything they had done, while still reporting completion.
- **Read line ranges, not whole files, and truncate every tool result at the
  source.** `grep -n` for the anchor, then read the 40 lines around it. Pipe long
  output through `head`/`tail`; grep a suite run for its summary lines rather than
  dumping it. This is the single biggest lever on cost and it compounds: every
  tool result stays in context for the rest of the session, so a 600-line file
  read whole is ~8k tokens re-sent on *every remaining turn*, and a worker that
  reads thirty files whole is carrying all thirty, forever. Measured: context grew
  **9-15x** over a worker's life, ~20k on turn one to 175-295k at the end.

  The counter-intuitive part, and the reason this is a *prevention* rule rather
  than a cleanup one: with prompt caching, **keeping context is usually cheaper
  than compacting it**, so the answer is not to summarise later — it is not to
  load the bloat in the first place.
- Let hooks run. **Never `--no-verify`.** State the expected duration.
- Coverage gates, formatters, and any repo-specific requirements.
- UI work must be *looked at*, not just tested — run the screenshot harness,
  build a before baseline first if baselines are gitignored, and check the
  tightest resolution. **Report the diff percentages and name the shots a human
  should open.** A percentage is evidence in both directions: on one issue the
  harness scored the very screen the ticket was about at 0.27% while unrelated
  screens moved 15–20%, and that number *was* the finding — the rows had been
  added below the fold, where the tests could see them and the player could not.
- **If your change lowers the test count, justify every deletion by name.** A
  rewrite legitimately kills tests for behaviour that no longer exists — but the
  same diff quietly drops coverage for behaviour that *does*. One worker went
  1875 to 1869 describing it as "replaced 11 tween tests with 5 clock-driven
  ones"; review found four of the deletions covered live behaviour (pause,
  resume, speed and a multi-cell layout case) and nothing had replaced them. List
  each deleted test and say what still covers it, or say plainly that nothing
  does.
- **Never run a `gh` write command** — no `issue edit`, `issue close`,
  `issue comment`, `pr create`. You own every mutation of GitHub state.
  Read-only `gh issue view` is fine if it genuinely needs more context.
- **Never push, never `git checkout main`, never merge.** Stop after the last
  commit.
- Named forbidden interactive scripts, and their safe equivalents.
- Adjacent small fixes are welcome as separate commits; a second feature is not —
  report it instead, and you will file it.
- Name the issues assigned to *other* agents so it leaves them alone.
- Leave the branch green.

**Stop when green.** The agent does not review itself and does not spawn its own
reviewer — you do that, in Step 5. Tell it so, and tell it to expect findings
back in the same conversation.

**The final report is the return value** — the user never sees the transcript, so
it must stand alone: issue number, branch, what changed and why, design calls
made, commit list, suite results, what moved in generated files and why that is
correct, what was deliberately left undone, and **whether the issue is fully
answered or needs a residual note.**

---

## Step 5 — When an agent finishes

**Verify before merging. Do not take the report at face value.** Agents are
usually right and occasionally confidently wrong.

### Always close the review loop back to the original agent

**Do this on every issue. It is the highest-value step in the command, and the
agent reviewing its own work is not a substitute for it.**

The loop is: worker commits → you verify → a **fresh review subagent** reads
`git diff main...HEAD` → its findings go back to the **same worker** via
`SendMessage` → the worker enacts what it agrees with → you re-verify → merge.

Two details make it work:

- **Tell the reviewer it may correct you.** Your brief names failure modes to
  hunt for, and some of them will be wrong. On one issue the brief asserted that
  4x replay speed would multiply a per-frame cost; the reviewer established that
  frame count is set by the display, not the speed multiplier, so 4x does *less*
  total work. Say "if a premise in this brief is wrong, say so" — and pass the
  correction on to the worker rather than quietly dropping it, or the worker acts
  on your error.
- **The reviewer must be fresh, and it must not be the worker.** An agent
  reviewing its own diff is the weakest possible check: it re-reads its own
  reasoning and finds it convincing. Spawn a separate agent, give it the worktree
  path, the sandbox rule, and **the failure modes to hunt for in this specific
  issue** — generic "review this" gets generic results. Ask it to verify the
  worker's highest-consequence claim by running something, not by reading.
- **The findings go back to the original worker, not to a new one.** Keep the
  `agentId` from each spawn and `SendMessage` the findings to it; it still holds
  its own reasoning and can say "I disagree, here is why". Frame it as a
  *decision, not a work order*, and say that disagreement is a valid outcome —
  across several runs workers have rejected reviewer suggestions and been right,
  once catching that a proposed one-line guard would have broken an unrelated
  path on first use.

What this loop caught in one nine-issue run, with every suite green throughout: a
voice-stealing regression the worker had introduced in the same function whose
docstring promised the opposite; a fix wired to one of two code paths, leaving the
bug reproducible on the first screen a new player sees; four rows added below the
fold where the tests could see them and the player could not; a verdict line that
picked its cause by branch order rather than magnitude; and a layout fix that paid
for horizontal space out of the vertical and re-clipped the thing it had fixed.

**Do not skip it to save time.** It roughly doubles wall-clock per issue and is a
small fraction of the worker that preceded it. If you are tempted to trade it
away, trade away a worker slot instead.

1. `git log --oneline main..<branch>` and `git diff --stat main...<branch>` —
   does the shape match the story? Is the worktree clean?
2. **Spot-check the highest-consequence claim** by reading that diff. If it cites
   a commit as evidence ("this shipped in abc1234"), verify that commit exists
   and says what they claim.
3. **Check the `Closes #N` trailer is actually there and names the right issue.**
   `git log main..<branch> --format=%B | grep -i '^closes #'`. A missing or
   misnumbered trailer is silent until you notice the issue never closed — or
   until it closes the wrong one.
4. **Check your own baselines before trusting a diff against them.** If you
   seeded anything for the agents — screenshot baselines, a golden set, a
   recorded suite count — verify it was built from the commit you think it was.
   In one run the screenshot baselines were seeded from a stale `out/` directory,
   so two agents reported large diffs on screens they had never touched and one
   nearly changed code to chase them. The check is cheap: regenerate in an idle
   worktree at the base commit and confirm the diff is empty. An unverified
   baseline makes every visual judgement downstream of it worthless.
5. Check overlap with what has landed since it branched:
   ```bash
   comm -12 <(git diff --name-only $(git merge-base main <b>)...<b> | sort) \
            <(git diff --name-only $(git merge-base main <b>)...main | sort)
   ```
6. Merge with `--no-ff` and a message explaining *why*, not just what.
7. **Note the turn count, and treat a high one as a finding.** Turns are the cost
   driver, and an agent that took 118 turns where a sibling took 42 is usually
   telling you its prompt was vague, not that its issue was hard. Feed that back
   into the next prompt rather than absorbing it.
8. **Re-run every suite on the merged result yourself**, and any project guard
   (balance, benchmarks, lint). A branch green in isolation can break on merge.
9. Remove the worktree, delete the branch, rotate the slot, update the state file.

### Resolving conflicts in generated files

When two branches both touch a derived file (goldens, snapshots, transcripts),
**do not hand-pick a side** — you will silently drop one branch's semantic change.
Take the side with the structural change, then **re-run the generator** so the
merged inputs produce the merged output. Then verify a second regeneration is a
no-op, which proves you landed on a fixed point.

### Closing issues

**The `Closes #N` trailer does the closing, and it fires on push, not on merge.**
GitHub sees the keyword when the commit lands on the default branch *on the
remote*. So:

- **If the user opted into pushing**, issues close on their own as you push. Do
  not also close them by hand.
- **If not — the default —** every issue stays open until the user pushes, at
  which point they all close at once. This is the right behaviour: the issue
  closes when the work becomes real. **Say so explicitly in the closing report**,
  with the list of numbers that will close, or the user will think the run failed
  its bookkeeping.
- **Close by hand only when no commit closes it**: the issue was stale, a
  duplicate, or the agent found it already shipped. Say why in the same breath —
  `gh issue close 16 -c "<reason>"` — and use `--reason "not planned"` when it is
  an abandonment rather than a completion.
- **An issue only partly answered stays open.** Edit the body down to what is
  left rather than closing it and filing a successor; the history is worth more
  than the tidiness. Strip the `Closes` trailer from the agent's commit if it
  claims more than it delivered.

### Filing what the agents found

**Open a new issue for every real finding an agent surfaced but correctly
declined to fix** — design calls that need the user, pre-existing debt too big to
bundle, bugs found in passing. Say why it was not done, and link the issue it came
out of. Losing these is the main way this process leaks value.

```bash
gh issue create --title "…" --label "found-by-agent" \
  --body-file /tmp/finding.md
```

Use `--body-file`, never `--body` — issue bodies are Markdown full of backticks
and newlines, and shell quoting mangles them quietly.

Tell the user in your final report which issues you opened, so they can close any
they do not want.

### Verify the bookkeeping

Issue edits produce no diff and no commit, so nothing fails if you write to the
wrong number. After the run:

```bash
gh issue list --state open  --json number,title,labels
gh issue list --state closed --limit 20 --json number,title,closedAt
```

Confirm the open list is what you expect, that nothing closed which you did not
intend, and that every issue you filed is there and readable. An empty result
from a verification command deserves the same suspicion as an error — see the
cwd note in 2a-bis, where `git status --porcelain <bad-path>` also "passes" by
printing nothing.

---

## Hard rules

- **You merge, agents never do.** `git checkout main` *fails* from a worktree
  when main is checked out in the primary tree, so the usual documented flow
  cannot work for them. Serializing merges through you also avoids racing on
  main's index.
- **You own every `gh` write.** No exceptions. Agents read at most.
- **Never push** unless the user opted in.
- **Never leave a worker slot idle** while the queue is non-empty — you are
  re-invoked on completion, so an empty slot means the run stalls until the user
  notices.
- **Report failures honestly.** If a suite fails, say so with the output. If an
  issue was parked, say what blocked it.
- If the user says to stop queueing, stop spawning immediately, let in-flight
  agents finish, merge them, and offer to kill them instead.

## Closing report

Summarize: what shipped, what each agent found that the issue did not know, what
was parked and why, **which issues will close on your next push and which you
closed by hand**, what you filed, any judgement calls the user should review, and
the final verified suite numbers. Lead with anything surprising — a stale issue
or a latent bug found on the way is usually worth more to the user than the
feature that was asked for.
