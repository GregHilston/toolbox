---
description: Complete verification - format, test build, validate
allowed-tools: Bash(nix:*), Bash(just:*), Bash(cd:*), Bash(find:*)
argument-hint: [hostname]
---

## Files to Check
!`find /home/ghilston/Git/toolbox/nixos -name "*.nix" -type f | wc -l` Nix files

## Task
Multi-step verification for **$1**:

### Step 1: Format
Run: `cd /home/ghilston/Git/toolbox/nixos && nix fmt .`
Report files changed.

### Step 2: Test Build
Run: `cd /home/ghilston/Git/toolbox/nixos && just ft $1`
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

If build fails, show error and suggest fixes.
