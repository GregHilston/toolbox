# Prep — Ready GitHub Issues for Agents

Take a list of GitHub issues, research each one, ask the user what only they can
answer, and **rewrite each issue body** so every one is either ready to hand to
an agent or explicitly labelled as not ready.

This is the interactive companion to `/orchestrate`. Run it while the user is
awake and present; run `/orchestrate` after, when they are not.

**Your output is a better issue, not a chat summary.** A decision that lives only
in this conversation is lost the moment the session closes. If you learn
something, write it into the issue body.

## Usage

```
/prep 16 23 41                                    # these issues
/prep https://github.com/owner/repo/issues/16     # URLs work too
/prep --label bug                                 # every open issue so labelled
/prep                                             # every open, unprepped issue
/prep 16 --deep                                   # one issue, exhaustively
```

Numbers, `#16`, and full URLs are all accepted. A URL naming a different repo is
a mistake worth catching — say so rather than silently prepping the wrong repo's
backlog.

Closed issues are out of scope. Closed **is** the "not doing" pile now, and
`/orchestrate` reads only open issues, so a decision to abandon something is
self-enforcing in a way a heading in a file never was.

---

## `gh` and the sandbox

Every `gh` call needs `dangerouslyDisableSandbox: true`. Sandboxed, the filtering
proxy intercepts TLS and `gh` refuses the certificate:

```
Post "https://api.github.com/graphql": tls: failed to verify certificate: x509: OSStatus -26276
```

That error is the sandbox — not the network, not the token. **`gh auth status`
fails the same way and misreports it as an invalid token**; do not go fix
credentials that are fine.

### Always edit with `--body-file`, never `--body`

```bash
gh issue view 16 --json body -q .body > /tmp/issue-16.md
# edit /tmp/issue-16.md
gh issue edit 16 --body-file /tmp/issue-16.md
```

`gh issue edit N --body "..."` passes the whole body through shell quoting, and
issue bodies are Markdown full of backticks, `$`, and newlines. It mangles them
quietly. Worse, **`--body` replaces the entire body** — a truncated argument
silently deletes the rest of the issue.

**Re-read every issue you edit.** This is the one real thing the file workflow
gave you for free: a body edit produces no diff to review, no commit to inspect,
and nothing fails if you wrote to the wrong number. `gh issue view N` afterwards
is the check, and it is not optional.

For a substantial rewrite, **show the user the proposed body before writing it.**
The original survives only in GitHub's edit-history dropdown, which is not
somewhere anyone thinks to look.

---

## The hard rule

**An issue that is too loosely defined to implement does NOT get handed to an
agent — ever — until the user has answered definitively.**

Do not soften this. Do not let an agent "use its judgement" on a vague issue, and
do not narrow the issue yourself to something buildable. Both are ways of
deciding on the user's behalf, and the user cannot review a decision they were
never shown. If they decline to answer, it stays blocked. That is a correct
outcome, not a failure.

An issue is **ready** only when all three hold:

1. **Definition of done** — you could tell whether it worked without asking.
2. **Decisions named and answered** — every fork the implementer would hit has an
   answer in the body, or an explicit "implementer's call" written down.
3. **Bounded scope** — you can say what is *not* included.

Archetype of a blocked issue, from a real backlog:

> **async game against friend** — "a whole new backend… add an email address to
> people's accounts… see all the games in progress… time until the game is
> forfeited"

That is four features (accounts, email delivery, a multi-game lobby UI, turn
expiry) with no provider chosen, no auth model, no timer values, and no MVP
boundary. An agent given that overnight will invent all four and be wrong about
most. It needs a real conversation, and if the user has not got time for one, it
stays blocked.

---

## Step 0 — Labels

State lives in labels, because `gh issue list --label prep:ready` filters
server-side and `/orchestrate` reads exactly that. Create them once per repo:

```bash
gh label create prep:ready   --color 0E8A16 --description "Specced; safe to hand to an agent"
gh label create prep:blocked --color B60205 --description "Needs a decision only the user can make"
gh label create size:S --color C5DEF5
gh label create size:M --color C5DEF5
gh label create size:L --color C5DEF5
```

`gh label create` on an existing label errors; that is fine, ignore it.

`prep:ready` and `prep:blocked` are mutually exclusive. When one goes on, the
other comes off — `gh issue edit N --add-label prep:ready --remove-label prep:blocked`.
Two agents' worth of confusion has come from an issue carrying both.

---

## Step 1 — Inventory

Fetch the issues in one call, not N:

```bash
gh issue list --state open --limit 200 \
  --json number,title,labels,body,createdAt,updatedAt
```

List every issue with a one-line paraphrase and its current labels. Show the user
the list before you start, so they can strike ones they no longer care about —
the cheapest triage available is closing.

## Step 2 — Research before asking

**Never ask a question the repository can answer.** From a real run: three of
eight items were stale — two features had already shipped (one three days
earlier, one six months earlier) and a third named the wrong screen. "Do you
still want this?" is a terrible question when the answer is "it shipped in
February."

For each issue, cheaply establish:

- **Has it already shipped?** `git log --oneline -S'<keyword>'`, grep for the
  feature's nouns, read the code it names. This is the highest-yield check.
- **Is the issue's stated *cause* still true?** Distinct from "has it shipped",
  and the one that got through a later run: three items were stamped `ready`
  whose symptom was real and whose files existed, but whose **diagnosis was
  wrong**. One said a renderer "silently drops" a field that had been threaded
  through *the day before*. One said a panel's numbers "drift as the game
  progresses" when the panel is hidden outside the building phase and cannot
  drift. One predicted which field a change would move, and it moved a different
  one. Each cost an agent the first stretch of its run to disprove. **If an issue
  explains *why* something is broken, open that code and check the
  explanation** — a `prep:ready` label claims you did.
- **Do the file/symbol references still exist?** Issues rot; code moves.
- **Is it self-consistent?** Look hard for two sentences that disagree. A real
  example: one said a keyword would read "the Tick's opening armour" in one
  paragraph and "what the Economy Pass left" in another — different numbers, and
  the contradiction was only caught mid-implementation.
- **Is it one item or several?** Split issues that are two unrelated jobs.
- **Is it coupled to another issue?** If A needs B first, say so in **both**
  bodies and link them (`#23`). Coupled items must go to one agent; two agents
  cannot share a dependency. GitHub's own "blocked by / blocking" fields are
  visible in `gh issue view` and are the better home for a hard dependency.
- **Rough size** — S / M / L, and whether it spans more than one subsystem.

Scale the effort: read inline for a handful; for a long backlog, delegate the
research to a few read-only agents (`Explore` or general-purpose) covering
several issues each, and keep the conclusions rather than the file dumps. Say
what you delegated.

## Step 3 — Classify

Give every issue exactly one:

| | Meaning | What you do to the issue |
|---|---|---|
| **READY** | Meets all three criteria | `prep:ready` + a `size:` label |
| **NEEDS-DECISION** | Implementable once the user answers | Ask (Step 4), then it becomes READY or BLOCKED |
| **BLOCKED** | Too vague to ask crisp questions about; needs a design conversation | `prep:blocked`, and a `## Still needs` list in the body |
| **STALE** | Already done, or describes code that no longer exists | Propose closing as completed, naming the commit that shipped it |
| **SPLIT** | Should be two or more issues | Open the children, cross-link, propose the parent's fate |
| **DROP** | Not worth doing | Propose closing as not planned |

Never leave an issue in NEEDS-DECISION at the end of a run. It is a transient
state, not a resting one.

## Step 4 — Ask

Use `AskUserQuestion`: up to 4 questions per call, 2–4 options each, and put a
recommendation first labelled "(Recommended)". Batch across issues so the user
answers in a few passes rather than dozens.

Rules that make this bearable for the user:

- **Ask only what changes the work.** If a sensible default exists and the cost
  of being wrong is low, pick it, state it, and move on.
- **Bring options, not open questions.** "Which email provider?" is work you
  pushed back onto them; "SES, Postmark, or SMTP-via-your-existing-host?" with
  trade-offs is a decision they can make in ten seconds.
- **Lead with your research.** "This shipped in `abc1234` — close it?" is one
  question that removes an entire item.
- **For a BLOCKED issue, go deep on that one issue** across several calls rather
  than sprinkling its questions among others. Cover: the MVP slice, external
  dependencies and credentials, data model changes, UI surface, and what is
  explicitly out of scope. Then re-classify — it becomes READY or it stays
  BLOCKED. Never leave it half-specified.
- If the user defers, that is an answer: label it `prep:blocked` and move on. Do
  not nag, and do not quietly proceed.

## Step 5 — Rewrite the body

This is the part that matters.

- **Fold the answers into the prose.** The body should now read as though it had
  always been well specified. **Do not append a Q&A section** and do not leave
  the answers in comments — an agent handed a twelve-comment thread has to work
  out which comment supersedes which, which is the exact failure this command
  exists to prevent. One body, current, authoritative.
- **Record decisions with their reasoning**, so the next reader does not reopen a
  settled question.
- **Say what is out of scope**, explicitly.
- Fix rotted file and symbol references while you are in there.
- Keep the title honest. If the body changed meaning, `gh issue edit N --title`.

A prepped body wants roughly this shape — enough structure that an agent can find
the parts, not so much that a two-line bug report becomes a document:

```markdown
<the problem, in the user's own voice, tightened>

## Done when
- [ ] …

## Decided
- <fork> → <answer>, because <reason>

## Out of scope
- …

## Where to look
`path/to/file.gd:120` — …
```

Drop any heading that would be empty. A `## Still needs` section replaces
`## Done when` on a blocked issue.

**Preserve the user's voice.** Issues are often written fast and in the first
person. Tighten and clarify, but do not launder them into corporate prose — the
informality carries intent, and a rewritten issue the author no longer recognises
is worse than a rough one they do. This matters more here than it did in the
file: with everything folded into the body, the original text survives only in
GitHub's edit history.

**Never close an issue the user has not agreed to close**, even an obviously
stale one. Propose; they confirm. Closing is cheap to undo and expensive to
notice.

## Step 6 — Verify

A file workflow gave you `git diff`. This one gives you nothing, so ask:

```bash
gh issue list --state open --json number,title,labels \
  -q '.[] | "\(.number)\t\([.labels[].name] | join(","))\t\(.title)"'
```

Check, every time:

- Every issue you prepped carries exactly one of `prep:ready` / `prep:blocked`.
- No issue carries **both**.
- Every `prep:ready` issue has a `size:` label.
- The issues you meant to close are closed, and nothing else is.
- Nothing you did not touch changed labels.

Then re-read the bodies you rewrote. Not a sample — all of them. Writing to the
wrong issue number is silent, and this is the only place it surfaces.

## Step 7 — Report and hand off

Tell the user:

- The counts: ready / blocked / closed-stale / split / dropped.
- **Which issues are ready, in a suggested run order**, noting coupled items that
  must go to one agent and items touching the same subsystem that must not run
  concurrently.
- **Which are blocked and exactly what each still needs** — this is the list they
  act on next.
- Anything your research contradicted, which is often the most valuable thing you
  found.
- Rough total size, so they can decide how much to run at once.

Then suggest the concrete next command, with the numbers filled in:

```
/orchestrate 16 23 41
```

---

## Notes

- **A closed issue is the "not doing" pile.** It needs no special handling and
  cannot be picked up by mistake, because `/orchestrate` reads open issues only.
  Add `wontfix` if the distinction from "done" is worth preserving, and close as
  `not planned` (`gh issue close N --reason "not planned"`) so GitHub renders it
  differently from a completed one.
- **Do not invent process the repo does not have.** Milestones, projects, and
  assignees are all available and mostly not worth it for one person. Labels plus
  a good body is the whole system.
- If the repo's `CLAUDE.md` states conventions for how work is tracked, respect
  them, and check the issues actually comply.
