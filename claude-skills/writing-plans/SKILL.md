---
name: writing-plans
description: |
  Turn a spec into an implementation plan of small, independently testable
  tasks with exact files, code, test commands and commits, written for an
  engineer with no context. Use when there is a spec and no code yet.
disable-model-invocation: true
model: inherit
---

# Writing plans

Adapted from [obra/superpowers](https://github.com/obra/superpowers) (MIT),
cut to the checklist and to this repo's conventions. Invoke by name; it is
not loaded on its own.

Write for a skilled engineer who knows nothing about this codebase or its
tools and has questionable taste. Everything they need is in the plan: which
files, what code, how to test it, when to commit. DRY, YAGNI, TDD, small
commits. Save it where the user says; otherwise `docs/plans/YYYY-MM-DD-<name>.md`.

## Before the tasks

- **Scope.** A spec that covers independent subsystems is several plans, one
  per subsystem, each producing working software on its own.
- **File map.** List every file created or modified and its one
  responsibility. Small, focused files; things that change together live
  together; follow the codebase's existing shape rather than restructuring.

## Tasks

A task is the smallest unit with its own test cycle that a reviewer could
reject on its own. Fold setup, config and docs into the task whose
deliverable needs them. Each step is one action of a few minutes:

```markdown
### Task N: <component>

**Files:** Create `path`, Modify `path:lines`, Test `path`
**Interfaces:** what this consumes from earlier tasks and what it produces for
later ones — exact names and types, since a task's implementer sees only
their task.

- [ ] Write the failing test           (the test code, verbatim)
- [ ] Run it, expect FAIL with <reason> (the command, verbatim)
- [ ] Write the minimal implementation (the code, verbatim)
- [ ] Run it, expect PASS
- [ ] Commit                           (`git add <files> && git commit -m "..."`)
```

## Plan header

Goal in one sentence. Architecture in two or three. Tech stack. The spec's
path, so it travels with the plan. Global constraints copied verbatim from
the spec: version floors, naming rules, platform requirements.

## Placeholders are plan failures

Never: "TBD", "add error handling", "write tests for the above", "similar to
Task N", a step that says what without showing how, or a name no task
defines.

## Self-review, then hand off

Skim the spec and point to the task that implements each requirement. Search
the plan for the placeholders above. Check that a name used in task 7 is the
name defined in task 3. Fix inline. Then offer the two ways to execute:
subagent per task with review between, or inline in this session with
checkpoints.
