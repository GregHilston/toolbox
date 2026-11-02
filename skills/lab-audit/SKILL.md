---
name: lab-audit
description: Full home-lab update pass. Review recent alerts, Dependabot alerts and PRs, stale image pins and coverage gaps, pitch an approve/hold list to Greg, then build one reviewed PR with exact deploy commands for him to run and verify the result. Use for /lab-audit.
disable-model-invocation: true
argument-hint: "[service…]"
---

# lab-audit

You are the orchestrator: you hold the procedure, talk to Greg, and own the commits. DeepSeek
workers do the reading. **Greg merges and deploys.** You branch, test and open the PR, then
verify after he runs it. With service names in the arguments, limit the pass to those.

The lab's facts live in its repo. Read these first: `docs/updating-services.md` (traps, and what
each lockfile runs), `docs/adding-a-service.md` (coverage), `docs/alerting.md`, `CLAUDE.md`. Then
search past findings: `grep -ril <service> ~/Git/notes/llm`.

## 1. Inventory

```bash
usage-mark.py start lab-audit
deepseek-preflight.py
lab-alerts.py --days 7
cd ~/Git/home-lab && scripts/service-audit.py --updates
gh pr list --state open
gh api "repos/GregHilston/home-lab/dependabot/alerts?state=open&per_page=100" --paginate
df -h /System/Volumes/Data
```

`service-audit.py` needs `secrets/.env`, so in a worktree read
`~/Library/Logs/service-audit-check.log` on dungeon instead.

**Done when** you hold six lists: alerts by group, coverage gaps, image bumps, images the script
could not check, Dependabot alerts per lockfile, and open PRs, each noting any overlap with this pass.

## 2. Alerts

For each group, run its runbook's read-only checks and record one of: still broken, recovered, or
false alarm. `OPEN` only means no all-clear arrived, so check the current state. A false alarm is a
bug: its fix joins this pass, with a test that fails first.

## 3. Coverage gaps

Fix each gap (the touchpoint in `adding-a-service.md`) or exempt it with a reason in
`scripts/service-audit.exempt`. A gap you cannot judge goes to Greg. For an image the script could
not check, add its repo to `RELEASE_REPOS` in `digest/digest/config.py`.

## 4. Research

Give each batch of bumps to a `pi-ask` worker, read-only, grouped by risk: release notes between
the pin and the target, the trap table, and the service's compose block and config. Each returns
**ship**, **care** (the extra steps) or **hold** (why), with any data migration, the rollback, and
any release it did not read. Rerun a thin report on Sonnet. Check for yourself what a verdict
rests on in live state, such as a setting in an app's database.

For lockfiles, find what the lockfile actually runs first (`updating-services.md`), and move only
flagged packages. Hold a resolution that jumps a direct dependency's major for its own change.

**Done when** every bump and lockfile has a verdict, and you can name what you could not check.

## 5. Pitch

Write the full table to `<scratchpad>/lab-audit.md`, and give Greg its path. Then ask one
`AskUserQuestion` with up to four questions, one per group: **ship**, **care**, majors, and fixes
(alerts and coverage). Each offers approve all, choose (he names them in Other), or hold.

## 6. Build

On one branch from `origin/main`: one commit per service, conventional, with no AI attribution lines.

- **Start each changed image once, with its real environment.** Release notes cannot show what a
  compose `environment:` does to a new build; on 2026-11-02 that took Caddy down. Use a scratch
  directory, `--network none` where it can run so, and never a production volume. Build on moria
  when it is awake, since dungeon has no RAM to spare, and read the output: some validators exit 0
  on failure.
- **Run the tests the change touches, on the interpreter that runs it,** and compare any failure
  with `origin/main`.
- **Write only what the output showed.** A claim goes in the PR after you have read its evidence.

**Done when** the PR's body holds what changed and why, what was left out and why, what was not
verified, test results, and staged deploy steps: a fresh snapshot, then lowest risk first, each
with the commands and checks that prove it, and the rollback.

## 7. Review

Run two reviews, side by side in one message: a Sonnet subagent on the deploy commands, pins and
claims, and a `pi-ask` worker on what a diff read misses. Each checks upstream source and the
scripts it calls. Verify each finding before taking it: reviewers are wrong too, and in both
directions. Fix what you accept, and say in your report what you rejected and why. Re-review any
fix to a deploy step.

## 8. Hand over

Give Greg the PR links in merge order and the deploy commands in the last message of the turn. Name
what each step takes down and what he must check by hand. Stop until he reports back.

## 9. Verify

Check each service by what it is for, not only that it runs: read the state a user would depend
on, such as a lock's state in Home Assistant, a real search, or an exporter's metric count. Recheck
after a few minutes, since first-minute numbers miss leaks and slow failures. A failure gets the
trap table's or runbook's fix, or a follow-up PR, and a report before anything else ships.

## 10. Write back

Put findings in `~/Git/notes/llm/`, and commit that repo. Add each new trap to the table in
`updating-services.md`, and a runbook line for each service fix. If this pass taught something about
running this skill, edit this file. End the report with `usage-mark.py report lab-audit`.
