# Roadmap Prep

Walk a roadmap item by item, research each one, ask the user what only they can
answer, and **rewrite the file** so every entry is either ready to hand to an
agent or explicitly marked as not ready.

This is the interactive companion to `/orchestrate`. Run it while the user is
awake and present; run `/orchestrate` after, when they are not.

**Your output is a better roadmap file, not a chat summary.** A decision that
lives only in this conversation is lost the moment the session closes. If you
learn something, write it into the entry.

## Usage

```
/roadmap-prep                   # every open H2 in ROADMAP.md
/roadmap-prep docs/PLAN.md      # a different file
/roadmap-prep "async game"      # one entry, deeply
```

Skip H2s under a "not doing" / "rejected" / "wontfix" H1 — read the file's own
structure. Mention how many you skipped and why.

---

## The hard rule

**An entry that is too loosely defined to implement does NOT get handed to an
agent — ever — until the user has answered definitively.**

Do not soften this. Do not let an agent "use its judgement" on a vague entry, and
do not narrow the entry yourself to something buildable. Both are ways of
deciding on the user's behalf, and the user cannot review a decision they were
never shown. If they decline to answer, the entry stays blocked. That is a
correct outcome, not a failure.

An entry is **ready** only when all three hold:

1. **Definition of done** — you could tell whether it worked without asking.
2. **Decisions named and answered** — every fork the implementer would hit has an
   answer in the entry, or an explicit "implementer's call" written down.
3. **Bounded scope** — you can say what is *not* included.

Archetype of a blocked entry, from a real roadmap:

> **async game against friend** — "a whole new backend… add an email address to
> people's accounts… see all the games in progress… time until the game is
> forfeited"

That is four features (accounts, email delivery, a multi-game lobby UI, turn
expiry) with no provider chosen, no auth model, no timer values, and no MVP
boundary. An agent given that overnight will invent all four and be wrong about
most. It needs a real conversation, and if the user has not got time for one, it
stays blocked.

---

## Step 1 — Inventory

List every open H2 with a one-line paraphrase. Show the user the list before you
start, so they can strike items they no longer care about — the cheapest triage
available is deletion.

## Step 2 — Research before asking

**Never ask a question the repository can answer.** Tonight's lesson from a real
run: three of eight entries were stale — two features had already shipped (one
three days earlier, one six months earlier) and a third named the wrong screen.
"Do you still want this?" is a terrible question when the answer is "it shipped
in February."

For each entry, cheaply establish:

- **Has it already shipped?** `git log --oneline -S'<keyword>'`, grep for the
  feature's nouns, read the code it names. This is the highest-yield check.
- **Is the entry's stated *cause* still true?** Distinct from "has it shipped",
  and the one that got through a later run: three entries were stamped `ready`
  whose symptom was real and whose files existed, but whose **diagnosis was
  wrong**. One said a renderer "silently drops" a field that had been threaded
  through *the day before the entry was prepped*. One said a panel's numbers
  "drift as the game progresses" when the panel is hidden outside the building
  phase and cannot drift. One predicted which field a change would move, and it
  moved a different one. Each cost an agent the first stretch of its run to
  disprove. **If an entry explains *why* something is broken, open that code and
  check the explanation** — a `ready` stamp claims you did.
- **Do the file/symbol references still exist?** Entries rot; code moves.
- **Is the entry self-consistent?** Look hard for two sentences that disagree.
  A real example: one entry said a keyword would read "the Tick's opening armour"
  in one paragraph and "what the Economy Pass left" in another — different
  numbers, and the contradiction was only caught mid-implementation.
- **Is it one item or several?** Split entries that are two unrelated jobs.
- **Is it coupled to another entry?** If A needs B first, say so in both. Coupled
  items must go to one agent; two agents cannot share a dependency.
- **Rough size** — S / M / L, and whether it spans more than one subsystem.

Scale the effort: read inline for a handful of entries; for a long roadmap,
delegate the research to a few read-only agents (`Explore` or general-purpose)
covering several entries each, and keep the conclusions rather than the file
dumps. Say what you delegated.

## Step 3 — Classify

Give every entry exactly one:

- **READY** — meets all three criteria. Nothing to ask.
- **NEEDS-DECISION** — implementable once the user answers specific questions.
- **BLOCKED** — too vague to ask crisp questions about yet; needs a design
  conversation, not a clarification.
- **STALE** — already done, or describes code that no longer exists.
- **SPLIT** — should become two or more entries.
- **DROP** — propose deletion, with the reason.

## Step 4 — Ask

Use `AskUserQuestion`: up to 4 questions per call, 2–4 options each, and put a
recommendation first labelled "(Recommended)". Batch across entries so the user
answers in a few passes rather than dozens.

Rules that make this bearable for the user:

- **Ask only what changes the work.** If a sensible default exists and the cost
  of being wrong is low, pick it, state it, and move on.
- **Bring options, not open questions.** "Which email provider?" is work you
  pushed back onto them; "SES, Postmark, or SMTP-via-your-existing-host?" with
  trade-offs is a decision they can make in ten seconds.
- **Lead with your research.** "This shipped in `abc1234` — delete the entry?"
  is one question that removes an entire item.
- **For a BLOCKED entry, go deep on that one entry** across several calls rather
  than sprinkling its questions among others. Cover: the MVP slice, external
  dependencies and credentials, data model changes, UI surface, and what is
  explicitly out of scope. Then re-classify — it becomes READY or it stays
  BLOCKED. Never leave it half-specified.
- If the user defers, that is an answer: mark it BLOCKED and move on. Do not
  nag, and do not quietly proceed.

## Step 5 — Rewrite the file

This is the part that matters. For each entry:

- **Fold the answers into the prose.** The entry should now read as though it had
  always been well specified. Do not append a "Q&A" section.
- **Record decisions with their reasoning**, so the next reader does not reopen a
  settled question.
- **Say what is out of scope**, explicitly.
- **Delete STALE entries**, noting in the commit message which commit shipped them.
- **Split SPLIT entries** into separate H2s.
- Fix rotted file and symbol references while you are in there.

Stamp each entry with one machine-readable line directly under its heading:

```
<!-- prep: ready | size: M | 2026-08-22 -->
<!-- prep: blocked | needs: email provider, auth model, MVP boundary -->
```

It is an HTML comment, so it is invisible in rendered markdown, greppable, and
`/orchestrate` can read it. Keep it to one line — nobody maintains more.

**Never edit the file by slicing between two headings you named.** Deleting an
entry by cutting from its heading to some other heading you remember being next
takes **everything in between** with it. Cut to the **next `^## ` line**, whatever
it happens to be. And never append an entry to the end of the file: a roadmap ends
with a "Deliberately not doing" H1, so an appended entry silently becomes one you
are not doing, and `/orchestrate` will skip it by design. Insert before that H1.

After rewriting, verify rather than assume:

```bash
grep -n "^## " ROADMAP.md                                    # every work item
grep -c "<!-- prep:" ROADMAP.md                              # every entry stamped?
awk '/^# Deliberately not doing/{f=1} f && /^## /{print}' ROADMAP.md   # what is buried
```

The counts should match what you set out to write, and nothing should be under
that H1 that you did not deliberately put there — including entries **the user
added by hand**, who appends to the end of the file and lands in the same trap.

Then **commit the roadmap** as its own change, with a message saying what moved
from blocked to ready and what was deleted as stale.

## Step 6 — Report and hand off

Tell the user:

- The counts: ready / blocked / stale-deleted / split / dropped.
- **Which entries are ready, in a suggested run order**, noting coupled items
  that must go to one agent and items touching the same subsystem that must not
  run concurrently.
- **Which are blocked and exactly what each still needs** — this is the list they
  act on next.
- Anything your research contradicted in the file, which is often the most
  valuable thing you found.
- Rough total size, so they can decide how much to run at once.

Then suggest `/orchestrate`, which will pick up only the READY entries.

---

## Notes

- **Never delete an entry the user has not agreed to delete**, even a stale one.
  Propose it; they confirm.
- **Preserve the user's voice.** These entries are often written fast and in the
  first person. Tighten and clarify, but do not launder them into corporate prose
  — the informality carries intent, and a rewritten entry the author no longer
  recognises is worse than a rough one they do.
- **Watch where new entries land.** Users append to the bottom of the file, which
  can drop them under a "Deliberately not doing" heading and make open work look
  rejected. Check the structure and move them if so.
- If the roadmap has a preamble stating what the file is *for* (decisions vs
  measurements, numbering conventions), respect it — and check the entries
  actually comply.
