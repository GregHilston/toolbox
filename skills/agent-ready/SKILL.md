---
name: agent-ready
description: Set up a repo so fresh agent sessions can build it unattended, with decisions on disk, issues with checkable Done when lines, and a ./verify.sh gate. Use when starting a project agents will build, before the first overnight run, or when an overnight run parks issues for unclear reasons.
disable-model-invocation: true
license: MIT
---

# Agent ready

A worker in an overnight run starts with an empty context and nobody to ask.
Everything it needs must be in the repo or the issue, and something other than
the worker must decide whether its work is good. This skill sets up both. Work
through the steps with Greg; each one says which skill does the work.

## 1. Decide, then write it down

Interview Greg with the `grilling` skill until the core loop, the look and feel,
and the scope are settled. Record them with `domain-modeling`:

- `docs/design.md`: the pitch, the core loop, the pillars, and what is out of
  scope. One page.
- `docs/adr/NNNN-*.md`: one per hard-to-reverse choice (engine version,
  networking model, art style), with the options rejected and why.
- `GLOSSARY.md`: the game's words, so every worker names things the same way.

## 2. Write CLAUDE.md as rules and pointers

Claude Code and pi both load `CLAUDE.md`, so one file serves either harness.
Keep it short: how to run and test the project, the conventions, and pointers to
the three files above. Point at files; do not paste their contents.

## 3. Build the gate before any feature

`./verify.sh` is the only judge the overnight loop trusts. It must:

- exit 0 on green and nonzero otherwise;
- print a few summary lines, with details in a log and each failure on one line
  as `ERROR <reason>`;
- finish in minutes, and time out rather than hang.

For a Godot game, run each step under `timeout`:

1. `godot --headless --import`, failing on `Error importing`.
2. gdUnit4 under `--headless`. It suits agents better than GUT, but both test
   runners exit 0 when no tests run, and both hang on a stuck `await`. Fail when
   the JUnit test count drops below a committed baseline.
3. A smoke test that starts a headless host and client on localhost ENet and
   asserts they connect and sync. It takes about six seconds.
4. A grep of every log for `SCRIPT ERROR` and `Parse Error`.

Put the Godot version and a list of banned Godot 3 patterns in `CLAUDE.md`, such as
`yield`, `KinematicBody2D` and `remote func`. Models drift into Godot 3 syntax,
worst of all in networking code. Make the gate pass on an empty project first.
Every failure seen overnight becomes a new check.

## 4. Cut issues a fresh session can finish

Use `to-tickets`, then `/prep`. Each issue fits one context window, links its
blockers with GitHub's native dependencies, and has a `Done when` section where
every line names a check `./verify.sh` runs, or ends in `(human)`. Feel ("jumping
feels floaty") is always `(human)`: no agent can grade it, so it waits for the
playtest instead of being self-graded.

## 5. Dry run

Run `overnight` attended on one small issue and read its log. Fix what confused
the worker in `CLAUDE.md` or the issue, not in the prompt.
