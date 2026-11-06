---
name: upkeep
description: Bring the toolbox repo's dependencies up to date in one reviewed PR, covering Dependabot PRs and alerts, npm audits, the flake lock, pinned versions, and test and CI health. Use for /upkeep.
disable-model-invocation: true
---

# Upkeep

One run produces one reviewed PR on `~/Git/toolbox`, with deploy commands. Greg merges and deploys, because `cd nixos && just dr <host>` needs his `sudo`.

Every claim in the PR comes from something you ran. A green check you didn't run goes under **Not tested**.

## 1. Survey

Run this in your shell (the `terminal` tool in Hermes, Bash in Claude Code, `bash` in pi). Start from this report and not Dependabot's alert page, which missed all 8 flagged packages on 2026-11-02:

```bash
upkeep-check.py
```

It is read-only. Exit 0 means no high-severity findings or failures, 1 means lines marked `LOOK`, 2 means lines marked `????` it could not check. Lines marked `note` still count as findings for step 3.

Then run `hostname -s` and pick where heavy work goes:

- **moria** takes builds and test suites, even when slow. Dungeon runs services, and `no-build-on-dungeon.py` blocks builds and `just test` there, so on dungeon send them to moria with `ssh moria`.
- **A host with builds running stays untouched.** A second build competes with whatever Greg is deploying.

Branch from `origin/main`. Run `just test` before changing anything, so failures you find later have a baseline.

**Done when** every `LOOK`, `note` and `????` line has a planned action or a stated reason to leave it.

## 2. Dependabot

- **PRs:** fold each open PR's bumps into your branch, at the latest version: `npm view` for npm packages, release tags for GitHub Actions. List the PRs you replace in the description. Read the changelog of every major bump against our config, starting with `dot/pi/.pi/agent/extensions/pi-permission-system/`.
- **Alerts:** treat each open alert as an audit finding in step 3.
- **Zero manifests:** a dependency graph with 0 manifests can't raise alerts. Report it, and point Greg at <https://github.com/GregHilston/toolbox/settings/security_analysis>.

**Done when** each PR is folded in or held back with a reason.

## 3. Audits

In each flagged lockfile's directory:

```bash
npm audit fix --package-lock-only --ignore-scripts
```

For each finding left, record why it stays, and whether the code runs:

- `dot/pi/extensions-available/` is parked, so nothing loads it.
- Homebrew `pi` bundles its own dependencies, and that copy is the one that runs. Only a newer `pi` changes it.

Read the advisory before calling something exposed or safe.

**Done when** the PR lists every remaining finding with its reason.

## 4. Version bumps

One commit per item, so each can be reverted alone.

**Flake lock.** Follow `nixos/CLAUDE.md` → "Flake lock bumps": evaluate every host, then build one for real, because evaluation and `--dry-run` both miss build failures.

```bash
cd nixos && nix flake update
```

**Build failures.** Read the log before retrying. `atuin`'s tests time out at high load, so a failure saying `timed out waiting for session` needs a quieter host. A rebuild on a quiet moria proves the package itself.

**ccstatusline.** Bump all three pins that `upkeep-check.py` reads. Render old and new against a scratch copy of the config, because `--config` rewrites the file it reads. If the new version migrates the schema, set the new version in the tracked file by hand and confirm a rerun changes nothing.

**pi packages.** Run `npm ci` in a scratch clone, then load them in isolation. `-ne` avoids conflicts with the installed copies, and `</dev/null` keeps `pi` from reading your script from stdin:

```bash
pi -ne -e <package-path> --mode json -p 'Reply with exactly: OK' </dev/null
```

**Done when** every host evaluates and one real build passes, or the PR says what stopped it.

## 5. Tests and CI

`just test` must pass on the final tree, and CI must pass on the PR. Fix a failing test at its cause, and name the cause in the PR.

A line in a CI log can be a mocked test's output, so confirm its source before using it as evidence.

**Done when** all checks are green on the final commit.

## 6. Review and PR

Have a subagent follow `claude-commands/pr.md` against the PR, and tell it to diff against `origin/main`, since local `main` can be stale. Enact what you agree with, and record what you reject and why. Run `pi-ask` for a second opinion on any script with logic.

Write the description to a file, then pass it with `--body-file`. It holds:

- what changed, and why;
- what Greg will notice after deploying;
- a verification table, and **Not tested**;
- deploy commands for each host, including `just hooks` after a lock bump, and when to avoid running them.

**Done when** the PR is ready for review and Greg has its link.

## 7. Notes

Write the run's findings to `~/Git/notes/llm/`, following that vault's `CLAUDE.md`, with `topics: ["[[toolbox]]"]`. Start from the newest `toolbox-*` note there, because it lists what earlier runs left alone on purpose.

After Greg deploys, run `upkeep-check.py` again. Its `Hosts` section shows whether dungeon and moria reached the lock. Check other hosts by hand.

**Done when** the note is written and the final report lists what still needs Greg.

## Tool mapping

| Capability | Claude Code | pi |
| --- | --- | --- |
| Review subagent | `Agent` tool, on Sonnet | `pi-subagents` if loaded; otherwise follow `claude-commands/pr.md` inline |
| Search this repo | `git grep`, because `rg` hides `dot/claude/.claude/` | same |
