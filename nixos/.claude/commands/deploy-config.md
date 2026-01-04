---
description: Deploy NixOS configuration after testing
allowed-tools: Bash(just:*), Bash(cd:*), Bash(git status:*)
argument-hint: [hostname]
---

## Pre-Deployment Check
!`cd /home/ghilston/Git/toolbox/nixos && git status --short`

## Target Host
$1

## Task
Deploy NixOS configuration to **$1**:

1. Confirm $1 is valid hostname (foundation, isengard, mines, vm-x86, vm-arm)
2. Check git status above - warn if uncommitted changes exist
3. Run: `cd /home/ghilston/Git/toolbox/nixos && just fr $1`
4. Monitor deployment and report status
5. If deployment fails, suggest rollback: `sudo nixos-rebuild --rollback switch`
