---
name: verify-agent-output
description: "Review an agent's tree with deterministic checks first: clean-tree install, diff, output profile, dead-symbol sweep. Use before judging any code an agent wrote."
version: 1.0.0
author: Greg Hilston
license: MIT
platforms: [macos, linux]
metadata:
  hermes:
    tags: [code-review, verification, data-quality, agent-output, gates]
    related_skills: [requesting-code-review, test-driven-development]
---

# Verify Agent Output

## Overview

Run the deterministic checks **before** forming an opinion, then judge what they
surface.

**Core principle:** a model judging code on its own catches roughly 45% of real
errors; the same model plus deterministic analysis reaches 94%. Your judgement
is the cheap half. Do the measuring first, so your opinion is anchored on what
the tree does rather than on how the code reads.

## When to Use

Whenever an agent hands back work and someone is about to call it done —
especially when its own tests pass. **A green suite is the situation this skill
exists for, not a reason to skip it.**

## Why a passing suite proves less than it looks

Every defect found in the review this skill is built from produced a
well-formed value of the right type in the right column. 86 tests passed, the
build exited 0, the install gate said OK, and five separate things in the
output were false.

A suite proves the tree *installs and runs*. It cannot prove the numbers
*mean* anything. These checks are for meaning.

## The Procedure

Run every step. Report the evidence, not a verdict.

### 1. Does it work for someone who was not here?

```bash
installs-from-clean.sh <workspace> [build-args]
```

Copies the tree without its venv, resolves from `pyproject.toml` alone with the
network off, and runs the suite and the entrypoint out of *that*. The venv that
accumulated during the run is the thing most likely to be lying.

If that script is not on PATH, do it by hand: copy the tree excluding `.venv`,
`.pytest_cache`, `__pycache__` and `.git`; `UV_OFFLINE=1 uv sync`; run the
suite and the entrypoint from the fresh environment.

**Stop and report if this fails.** Nothing below matters yet.

### 2. Read the diff, not the tree

```bash
git -C <workspace> log --oneline
git -C <workspace> diff <base>..HEAD --stat
git -C <workspace> diff <base>..HEAD
```

A tree is too large to review and you will skim it. A diff is the decision the
agent actually made.

Four shapes to hunt, in order of how often they bite:

| shape | looks like | why it bites |
| --- | --- | --- |
| a default that hides a gap | `map.get(k, "something")` over an enum | avoids an exception without finding out why one would fire |
| a constant where a mapping belongs | a field hardcoded for every row | a decision nobody made, applied everywhere |
| absence recorded as a value | `False` meaning "we did not look" | the next reader cannot tell it from a measurement |
| declared and never reached | an unused Protocol, a bypassed DTO | the contract it claims to enforce is not enforced |

### 3. Profile the output against its input

This is the step that catches what code review misses. For every generated
file, ask the data:

```bash
# Does every category come from a source that could produce it?
# A cross-tab that is not a function is a mapping bug.
<cross-tab each enum-ish column against the column naming its origin>

# Does a field's null rate match the field it is derived FROM?
# `is_freemail = false` on a row with no email is absence sold as a finding.
<compare null counts of derived column vs its source column>

# Is a generated per-row string actually per-row?
# If one value covers more than a few percent of rows, it is a template.
<count distinct values; show the most common and its share>

# Do the enum values in the OUTPUT cover the distinct values in the INPUT?
<distinct values of each source enum field vs distinct values emitted>
```

The last one is the highest-yield single check. Run it against the raw source
with `jq -r '.[].<field>' file.json | sort | uniq -c | sort -rn` and compare.

### 4. Sweep for code nothing reaches

```bash
# For each symbol the diff introduced, count uses that are not its definition.
grep -rn "<symbol>" src tests | grep -vE "def <symbol>|class <symbol>" | wc -l

# Declared dependencies that are never imported.
grep -rEn "^\s*(import|from) <dep>" src | wc -l
```

Zero uses on something newly written is not tidiness — it is a signal that a
contract was described instead of enforced. Activating a bypassed validator
often fails immediately, and that failure is the finding.

### 5. Lint, if the project declares one

```bash
uv run ruff check src tests    # or the project's own linter
```

## Reporting

Report findings ranked by consequence, each with:

- **what** is wrong, in one sentence
- **where** — file and line
- **evidence** — the command and its output, or a count from the data
- **how many rows / callers / cases** are affected

Never report a finding you have not evidenced. "This looks fragile" wastes the
builder's turn. "Line 47 maps three of eight `type_desc` values and defaults
the rest into a category belonging to another source file; 2,120 rows affected"
is actionable in one read.

**Request one focused revision at a time.** A list of twelve findings is a list
nobody acts on.

## What This Skill Will Not Do

It does not edit the code. If you are the reviewer, you report; the builder
fixes. A reviewer with a stake in the code is not a reviewer.
