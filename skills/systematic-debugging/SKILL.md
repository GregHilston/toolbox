---
name: systematic-debugging
description: |
  Find the root cause before proposing any fix: reproduce, read the error,
  diff against what changed, form one hypothesis, test it minimally. Use for
  a bug, a failing test, a build failure, or "I already tried three fixes".
disable-model-invocation: true
model: inherit
---

# Systematic debugging

Adapted from [obra/superpowers](https://github.com/obra/superpowers) (MIT),
cut to the checklist. Invoke by name; it is not loaded on its own.

**No fix without a root cause.** A symptom fix is a failure even when the test
goes green. Announce which phase you are in as you go.

## Phase 1 — Investigate

1. **Read the error completely.** The whole stack trace, every line number,
   every path. It usually names the cause.
2. **Reproduce it on demand.** Exact steps, every time. If it will not
   reproduce, gather more data; do not guess.
3. **Diff against what changed.** `git diff`, recent commits, new
   dependencies, config, environment.
4. **Across component boundaries, instrument before theorising.** Log what
   enters and leaves each layer (CI → build → sign, API → service → DB), run
   once, and let the evidence say which layer breaks.
5. **Trace bad values backwards** to where they originate. Fix at the source.

## Phase 2 — Find the pattern

- Locate working code that does the same thing in this codebase.
- If following a reference implementation, read all of it, not the first
  screen.
- List every difference between working and broken, however small.

## Phase 3 — One hypothesis, one change

- State it: "X is the root cause because Y."
- Make the smallest change that tests it. One variable at a time.
- If it did not work, form a new hypothesis. Do not stack fixes.
- If you do not understand something, say so and go find out.

## Phase 4 — Fix

1. Write the failing reproduction first: a test if there is a framework, a
   one-off script if not.
2. One fix for the identified cause. No "while I'm here" changes.
3. Verify: the reproduction passes, the rest of the suite still passes, the
   original symptom is gone (see `/verification-before-completion`).

**Three failed fixes means stop.** That is evidence of an architectural
problem, not a fourth attempt. Say so and discuss before touching code again.

## Rationalisations to refuse

| Thought | Reality |
| --- | --- |
| "It's obvious, just try it" | Obvious fixes that were wrong got you here. |
| "No time for process" | Guessing is slower than reading. |
| "I'll add a workaround for now" | Workarounds are the bug in a new place. |
| "It's probably X" | Probably is a hypothesis. Test it. |
