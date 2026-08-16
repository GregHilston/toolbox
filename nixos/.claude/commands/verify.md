---
description: Complete verification - format, test build, validate
allowed-tools: Bash(nix:*), Bash(just:*), Bash(find:*)
argument-hint: [hostname]
---

## Files to Check
!`find . -name "*.nix" -type f | wc -l` Nix files

## Task
Multi-step verification for **$1**:

### Step 1: Format
Run: `nix fmt .`
Report files changed.

### Step 2: Test Build
Pick the recipe by platform:
- **Darwin** (dungeon, moria, citadel): `just dt $1`
- **NixOS** (foundation, isengard, home-lab, rohan, mines): `just ft $1`

Report success/failure.

### Step 3: Validation
Check for:
- Missing module imports
- Conflicting options
- Syntax errors

### Summary
Report:
- Files formatted: X
- Build result: SUCCESS/FAIL
- Issues found: [list]
- Ready to deploy: YES/NO

If the build fails, show the error and suggest fixes.
