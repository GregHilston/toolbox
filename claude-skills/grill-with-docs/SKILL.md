---
name: grill-with-docs
description: |
  Relentless interview to sharpen a plan or design that ALSO leaves a paper trail:
  writes ADRs for hard/surprising/trade-off decisions and maintains a CONTEXT.md
  glossary of canonical domain terms, inline as you go. Run before building, when
  the plan is undefined and domain vocabulary is unsettled.
model: inherit
disable-model-invocation: true
allowed-tools: Read, Grep, Glob, Write, Edit
---

# Grill With Docs

Run a grilling interview (see below) AND capture alignment artifacts as you talk —
so the shared understanding survives the session. Do not enact the plan until the
user confirms shared understanding.

## Interview protocol

Interview the user about every aspect of the plan, one question per turn, waiting
for feedback before continuing (multiple questions at once is bewildering). Walk
each branch of the design tree depth-first, resolving dependencies between
decisions one-by-one. For each question, provide your **recommended answer**.
If a *fact* can be found in the codebase, look it up (Grep/Glob/Read); the
*decisions* are the user's — put each to them and wait.

## Leave a paper trail (inline, as you go)

**Glossary — `CONTEXT.md`:** when fuzzy language gets sharpened into a canonical
term, write it to `CONTEXT.md` at the repo root immediately. Keep it a pure
glossary (no implementation details, no spec). Follow `CONTEXT-FORMAT.md` in this
skill directory. Flag mismatches between the user's words and the documented terms.

**Decisions — ADRs:** record an ADR in `docs/adr/NNNN-slug.md` **only** when all
three hold: (1) hard to reverse, (2) surprising without context, (3) the result of
a real trade-off. Skip otherwise — keep the trail lean. Follow `ADR-FORMAT.md` in
this skill directory (create `docs/adr/` lazily; number by scanning for the highest
existing +1).

## Termination

Stop when branches are resolved/deferred or the user says stop. End with a summary
of resolved decisions, deferred items, ADRs written, and glossary terms added.
This is the front of the pipeline: grill-with-docs → to-spec → to-tickets → implement.
