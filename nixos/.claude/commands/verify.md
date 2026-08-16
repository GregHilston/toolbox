---
description: Complete verification - format, test build, validate
allowed-tools: Bash(nix:*), Bash(just:*), Bash(find:*), Bash(wc:*), Bash(git rev-parse:*)
argument-hint: [hostname]
---

## Files to Check
!`find "$(git rev-parse --show-toplevel)/nixos" -name "*.nix" -type f | wc -l` Nix files

## Task
Multi-step verification for **$1**:

### Step 1: Format
Run `nix fmt .` from the `nixos/` directory — it formats the current directory, so
running it from a subdirectory silently formats only that subtree.
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
