# Orchestrate Roadmap Work

Drive a roadmap to completion by spawning one subagent per H2 section, each in
its own git worktree, while you act as orchestrator: you merge, you own the
roadmap file, and you never stop until the queue is drained or the user says so.

**You are the orchestrator. You do not implement roadmap items yourself.** Your
job is preflight, spawning, verifying, merging, and bookkeeping.

## Usage

```
/orchestrate                    # every H2 in ROADMAP.md
/orchestrate docs/PLAN.md       # a different file
/orchestrate --max 4            # stop after 4 items (usage-limit friendly)
```

The roadmap file defaults to `ROADMAP.md` at the repo root. Any H2 (`## …`) is
one work item, **except** H2s nested under a "not doing" / "rejected" / "wontfix"
H1 — read the file's own structure and skip those.

---

## Step 0 — Has the roadmap been prepped?

Check whether entries carry a prep marker:

```bash
grep -c "<!-- prep:" ROADMAP.md
```

`/roadmap-prep` stamps each entry `<!-- prep: ready | size: M | ... -->` or
`<!-- prep: blocked | needs: ... -->` after researching it and getting the user's
answers.

- **Markers present** — spawn agents only for `ready` entries. Never pick up a
  `blocked` one; it is marked blocked because the user has not answered something
  only they can answer, and an agent given it overnight will invent an answer.
  Use the `size` hints to order the queue and to warn about total cost.
- **No markers** — say so, and offer to run `/roadmap-prep` first. If the user
  would rather go straight to work, do your own lighter triage before spawning:
  drop anything with no implementable spec (question 2 below), and check each
  remaining entry for whether it has already shipped.

An unprepped roadmap is the main source of wasted overnight runs. In one real
run three of eight entries turned out to be stale or misdescribed, and one
contained two sentences contradicting each other.

---

## Step 1 — Ask before you begin

Ask these with `AskUserQuestion` in ONE call. They change what you do, and the
user is usually about to walk away, so getting them wrong costs the whole run.

1. **Model / effort.** The Agent tool takes `model` (family only: `opus`,
   `sonnet`, `haiku`, `fable`) and has **no effort parameter** — per-agent effort
   exists only inside a `Workflow` script. You cannot pin a point release like
   "Opus 4.8". Say so plainly rather than pretending you can.
2. **Items with no implementable spec.** Almost every roadmap has entries that
   are one vague line, or that the entry itself says are the user's design call.
   Offer: design-doc-only / full autonomous implementation / skip. Never silently
   build a large feature on a guess.
3. **Push policy.** Default to *not* pushing. Check for a pre-push hook first —
   many repos deploy on push, and deploying at 3am can drop live users.
4. **Failure policy.** Default: park the branch unmerged, note it, keep going.
5. **Sandbox** — only after the preflight below tells you the answer.

Also tell the user up front which items you expect **not** to finish, so
"the roadmap will be empty by morning" is never an implied promise you can't keep.

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

### 2b. Does a worktree checkout even work sandboxed?

```bash
git worktree add worktrees/probe -b probe
```

This commonly fails with `Operation not permitted` on tracked files under
`.claude/`, `.mcp.json`, `.vscode/`, plus `could not lock config file .git/config`
— the sandbox denies those paths, and git must write every tracked file. If so,
**worktree add/remove must run with `dangerouslyDisableSandbox: true`**, and you
should do it yourself rather than delegating it.

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

- **Interactive scripts.** Anything that waits on typed input hangs an
  unattended agent forever. Grep for `read -p`, `input(`, confirmation prompts.
  Name them in the prompt as forbidden, and name the non-interactive equivalent.
- **Hooks.** What do pre-commit and pre-push actually run?
- **Generated/derived files.** Goldens, snapshots, lockfiles, generated themes.
  Note the regeneration command — you will need it at merge time.
- **Gitignored test baselines** (e.g. screenshot baselines). If they are not
  committed, each agent must build its own before/after, and a diff against your
  baseline is meaningless.

**Tear the probe down completely** and confirm `git status` is clean before
proceeding.

---

## Step 3 — Plan the queue

- **Merge coupled items into one agent.** If item A names item B as a
  prerequisite, or they want the same regeneration/verification pass, they are
  one unit. Two agents cannot share a dependency.
- **Serialize items that touch the same subsystem.** Two agents editing the same
  screen or module will conflict at merge. Sequence them; parallelize across
  unrelated areas.
- **Start the largest item first** so it has the most wall-clock.
- **Default to 2 concurrent agents**, and run **rolling**: refill a slot the
  moment one finishes rather than waiting for both. Strict pairs waste hours when
  a 10-minute item is paired with a 3-hour one.

Write the queue into a state file (`.claude/orchestrate-state.md`, gitignored) —
item, branch, status, notes. If your context is compacted mid-run, this is the
only thing that lets you pick up cleanly. Update it at every transition.

---

## Step 4 — The agent prompt

Spawn with the Agent tool, `subagent_type: "general-purpose"`, the agreed model.
**Create the worktree yourself first** so you control the branch name.

Every prompt must contain:

**Working directory.** The absolute worktree path, its branch, and the commit it
branched from. Plus: never edit the primary checkout, never touch a sibling
worktree.

**The sandbox rule, stated as settled fact** with the reason, so the agent does
not spend twenty tool calls rediscovering it.

**Check whether it already shipped.** *This is the highest-value instruction in
the whole command.* Roadmaps are pruned less often than they are appended to. In
one real run, **three of eight entries were stale or misdescribed** — two features
had already shipped (one three days earlier, one six months earlier) and a third
pointed at the wrong screen. Tell the agent to establish what exists via
`git log` **before** writing code, and to report "stale / partly done / genuinely
missing" as the first line of its report. If you find evidence of prior work
during preflight, hand it over.

**The task**, quoted verbatim from the roadmap, plus the docs it should read
first. If the entry is detailed, say "this is a decision already made, follow it;
if you believe it is wrong, say so loudly rather than silently substituting your
own."

**The decisions it must make alone**, named explicitly, with "take the
conservative option and flag it in your report." Nobody is awake; an agent that
stalls on a design question wastes the whole slot.

**Standing rules:**
- Conventional atomic commits; docs and tests updated *in the same commit* as the
  change they describe.
- Let hooks run. **Never `--no-verify`.** State the expected duration.
- Coverage gates, formatters, and any repo-specific requirements.
- UI work must be *looked at*, not just tested — run the screenshot harness, build
  a before baseline first if baselines are gitignored, and check the tightest
  resolution.
- **Never edit the roadmap file** — you own it, and otherwise every branch
  conflicts on it.
- **Never push, never `git checkout main`, never merge.** Stop after the last commit.
- Named forbidden interactive scripts, and their safe equivalents.
- Adjacent small fixes are welcome as separate commits; a second feature is not.
- Name the items assigned to *other* agents so it leaves them alone.
- Leave the branch green.

**Self-review.** When green, spawn ONE review subagent to adversarially review
`git diff main...HEAD`, given the worktree path and the sandbox rule. Tell it what
failure modes to hunt for *in this specific item* — generic "review this" gets
generic results. Enact all feedback it agrees with as further commits; report what
it rejected and why.

**The final report is the return value** — the user never sees the transcript, so
it must stand alone: branch, what changed and why, design calls made, commit list,
suite results, what moved in generated files and why that is correct, what was
deliberately left undone, and **whether the roadmap entry can be deleted or needs
a residual note**.

---

## Step 5 — When an agent finishes

**Verify before merging. Do not take the report at face value.** Agents are
usually right and occasionally confidently wrong.

1. `git log --oneline main..<branch>` and `git diff --stat main...<branch>` —
   does the shape match the story? Is the worktree clean?
2. **Spot-check the highest-consequence claim** by reading that diff. If it cites
   a commit as evidence ("this shipped in abc1234"), verify that commit exists
   and says what they claim.
3. Check overlap with what has landed since it branched:
   ```bash
   comm -12 <(git diff --name-only $(git merge-base main <b>)...<b> | sort) \
            <(git diff --name-only $(git merge-base main <b>)...main | sort)
   ```
4. Merge with `--no-ff` and a message explaining *why*, not just what.
5. **Re-run every suite on the merged result yourself**, and any project guard
   (balance, benchmarks, lint). A branch green in isolation can break on merge.
6. Update the roadmap and commit it separately.
7. Remove the worktree, delete the branch, rotate the slot.

### Resolving conflicts in generated files

When two branches both touch a derived file (goldens, snapshots, transcripts),
**do not hand-pick a side** — you will silently drop one branch's semantic change.
Take the side with the structural change, then **re-run the generator** so the
merged inputs produce the merged output. Then verify a second regeneration is a
no-op, which proves you landed on a fixed point.

### Roadmap bookkeeping

- Delete an entry only when its asks are actually delivered.
- **Add new H2 entries for real findings the agents surfaced but correctly
  declined to fix** — design calls that need the user, pre-existing debt too big
  to bundle. Say why it was not done. Losing these is the main way this process
  leaks value.
- Tell the user in your final report which entries you added, so they can delete
  any they do not want.

**Never edit the roadmap by slicing between two headings you named.** Both of
these have silently destroyed work in a real run:

- *Deleting a delivered entry* by cutting from its heading to some other heading
  you remember being next takes **everything in between** with it — including
  entries filed earlier in the same run, which is exactly when the file is
  changing under you. Cut from the entry's own heading to the **next `^## ` line**,
  whatever it happens to be, not to a named one.
- *Appending a new entry* with `content + new_entry` puts it at the end of the
  file — and a roadmap ends with a "Deliberately not doing" H1, so the entry
  silently becomes something you are **not** doing, which this command then skips
  by design. Insert **before** that H1, never after it.

The user also edits this file while you run, by hand, and appends to the end —
so their entries land in that same trap. Check for them.

After every roadmap edit, verify rather than assume:

```bash
grep -n "^## " ROADMAP.md                                    # every work item
awk '/^# Deliberately not doing/{f=1} f && /^## /{print}' ROADMAP.md   # what is buried
```

Confirm the first list is what you expected, and that the second contains only
entries you genuinely mean to abandon. A dangling reference in the run-order list
pointing at an entry that no longer exists is the usual first symptom.

---

## Hard rules

- **You merge, agents never do.** `git checkout main` *fails* from a worktree
  when main is checked out in the primary tree, so the usual documented flow
  cannot work for them. Serializing merges through you also avoids racing on
  main's index.
- **You own the roadmap file.** No exceptions.
- **Never push** unless the user opted in.
- **Never leave zero agents running** while items remain — you are re-invoked on
  completion, so an empty slot means the run stalls until the user notices.
- **Report failures honestly.** If a suite fails, say so with the output. If an
  item was parked, say what blocked it.
- If the user says to stop queueing, stop spawning immediately, let in-flight
  agents finish, merge them, and offer to kill them instead.

## Closing report

Summarize: what shipped, what each agent found that the roadmap did not know,
what was parked and why, what you added to the roadmap, any judgement calls the
user should review, and the final verified suite numbers. Lead with anything
surprising — a stale entry or a latent bug found on the way is usually worth more
to the user than the feature that was asked for.
