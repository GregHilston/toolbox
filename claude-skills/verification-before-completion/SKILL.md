---
name: verification-before-completion
description: |
  Run the command that proves a claim before making it: tests, build, lint,
  the original symptom. Use before saying done, fixed, or passing, and before
  a commit or PR.
disable-model-invocation: true
model: inherit
---

# Verification before completion

Adapted from [obra/superpowers](https://github.com/obra/superpowers) (MIT),
cut to the checklist. Invoke by name; it is not loaded on its own.

**No completion claim without fresh evidence.** If the verifying command did
not run in this message, the claim cannot be made in this message.

## The gate

Before any "done", "fixed", "passes", "works":

1. **Identify** the command that proves it.
2. **Run** it, in full, now. Not a partial, not an earlier run.
3. **Read** the whole output: exit code, failure count, warnings.
4. **Compare** the output to the claim. If it does not confirm it, report the
   actual state with the output.
5. Only then make the claim, with the evidence.

## What counts

| Claim | Needs | Does not count |
| --- | --- | --- |
| Tests pass | Test run: 0 failures | An earlier run, "should pass" |
| Lint clean | Linter run: 0 errors | A partial check |
| Build succeeds | Build: exit 0 | Lint passing, logs "look fine" |
| Bug fixed | Original symptom re-tested | Code changed, assumed fixed |
| Regression test works | Red → green → red on revert → green | It passed once |
| Subagent finished | The diff, read | The agent's own report |
| Requirements met | Checklist against the plan, line by line | Tests passing |

## Words that mean you have not verified

"should", "probably", "seems to", "looks right", "Great!", "Done!" before the
command ran. Also: "just this once", "I'm confident", "linter passed" (a linter
is not a compiler), "partial check is enough".
