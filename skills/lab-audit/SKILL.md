---
name: lab-audit
description: Pass over every home-lab service. Find stale image pins and coverage gaps (probe, Homepage, backup), research each update's release notes with subagents, pitch an approve/hold list to Greg, then ship approved updates one at a time on dungeon and verify each. Use for /lab-audit.
disable-model-invocation: true
argument-hint: "[service…] [deploy]"
---

# lab-audit

You are the orchestrator. Subagents read release notes; you hold the procedure, talk to
Greg, and own the commits. **Pitch mode** is the default: nothing ships until Greg approves
it. With `deploy` in the arguments, ship the bumps your review calls safe without asking;
a major, or a bump that migrates a database, still waits for Greg. With service names in
the arguments, limit the pass to those.

The procedure lives in the lab repo: `~/Git/home-lab/docs/updating-services.md` for
updates and `~/Git/home-lab/docs/adding-a-service.md` for coverage. Read both and
`~/Git/home-lab/CLAUDE.md` first.

## 1. Inventory

```bash
cd ~/Git/home-lab && scripts/service-audit.py --updates
gh pr list --author app/dependabot
```

**Done when** you hold three lists: open coverage gaps, bumps available (with Dependabot
PRs matched to them), and images the script could not check.

## 2. Coverage gaps

For each gap, decide: fix it (the matching touchpoint in `adding-a-service.md`) or exempt
it with a reason in `scripts/service-audit.exempt`. A gap you cannot judge goes to Greg.
For an image the script could not check, add its GitHub repo to `RELEASE_REPOS` in
`digest/digest/config.py` when it has releases.

## 3. Research the bumps

One subagent per bump, all in one message, in parallel. Use `model: "haiku"` for a patch
release and `model: "sonnet"` for a minor or a major. Each brief carries the service, the
pin and the target, a pointer to `docs/updating-services.md` (its trap table) and
`CLAUDE.md`, and these instructions:

- read every release between the pin and the target on GitHub, not only the latest;
- read-only: edit nothing, restart nothing;
- return a verdict, **ship**, **care** (the extra steps, such as a backup, a config edit or
  the gluetun group recreate) or **hold** (why), plus any database migration and the
  rollback.

A major, or any bump that migrates a database, also gets a DeepSeek second opinion through
the `pi-ask` skill. **Done when** every bump has a verdict with the releases it read.

## 4. Pitch

Write the full table (service, pin → target, verdict, why, extra steps) to
`<scratchpad>/lab-audit.md` and give Greg its path. Then ask one `AskUserQuestion` with up
to four questions, one per group: **ship** verdicts, **care** verdicts, majors, and
coverage fixes. Each question offers approve all, choose (he names them in Other), or
hold. In `deploy` mode, say you are shipping the ship verdicts and ask only about the rest.

## 5. Ship, one at a time

Follow Ship one in `updating-services.md` for each approved bump, in order of risk, lowest
first: backup check, pin change, tests, one commit per service (conventional,
`chore(deps): <svc> <old> -> <new>`, no AI attribution lines), push, deploy on dungeon,
verify. A Dependabot PR is merged instead of re-edited. **A bump is done only when its
verify passes.** One that fails gets rolled back and reported before the next one ships.

Coverage fixes ship the same way, one commit per idea.

## 6. Report

Per service: shipped (commit and verify evidence), held (why), or rolled back (what
broke). Re-run `scripts/service-audit.py` and paste its summary line. If this pass found a
new trap, add a row to the trap table in `updating-services.md`; if it taught something
about running this skill, edit this file.
