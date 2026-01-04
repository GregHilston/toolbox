---
description: Create commit, optionally push and/or create PR
allowed-tools: Bash(git add:*), Bash(git status:*), Bash(git diff:*), Bash(git commit:*), Bash(git branch:*), Bash(git log:*), Bash(git push:*), Bash(cd:*), Bash(gh:*)
argument-hint: [message] [--push] [--pr]
---

## Current State
!`cd /home/ghilston/Git/toolbox/nixos && git branch --show-current`
!`cd /home/ghilston/Git/toolbox/nixos && git status --short`
!`cd /home/ghilston/Git/toolbox/nixos && git log --oneline -5`

## Arguments
$ARGUMENTS

## Task
Create a commit following conventional commits format.

**Parse arguments:**
- If `--push` is present: also push after committing
- If `--pr` is present: also push and create a PR after committing
- Everything else is the commit message

**Workflow:**

1. Review changes (shown in git status above)
2. Stage changes if needed (use `git add` for untracked/modified files)
3. Analyze recent commit style (shown in log above)
4. Create commit with the message from arguments
   - Use conventional format: fix:, feat:, docs:, chore:, refactor:
   - Keep it concise (1-2 sentences)
5. Report commit hash and files changed

**If --push or --pr:**
6. Push to origin: `git push origin <current-branch>`

**If --pr:**
7. Create PR using `gh pr create` with a summary based on commit message

**Examples:**
- `/commit feat: add new module` → commit only
- `/commit feat: add new module --push` → commit and push
- `/commit feat: add new module --pr` → commit, push, and create PR

CRITICAL: Do NOT add "Generated with Claude Code" or "Co-Authored-By" to commit message.
