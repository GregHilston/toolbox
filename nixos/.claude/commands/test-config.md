---
description: Test a host configuration without switching
allowed-tools: Bash(just:*), Bash(git diff:*)
argument-hint: [hostname]
---

## Available Hosts
!`just list-hosts`

## Current Changes
!`git diff --stat HEAD || echo "No changes"`

## Task
Test the configuration for **$1** without deploying:

1. Verify $1 appears in the hosts list above.
2. Pick the recipe by platform — this repo has both, and the wrong one fails:
   - **Darwin** (dungeon, moria, citadel): `just dt $1`
   - **NixOS** (foundation, isengard, home-lab, rohan, mines): `just ft $1`
3. Monitor for errors/warnings.
4. Report results and suggest fixes if the build fails.

Do NOT deploy — this is test-only.
