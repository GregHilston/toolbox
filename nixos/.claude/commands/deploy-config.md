---
description: Deploy a host configuration after testing
allowed-tools: Bash(just:*), Bash(git status:*)
argument-hint: [hostname]
---

## Pre-Deployment Check
!`git status --short`

## Available Hosts
!`just list-hosts`

## Target Host
$1

## Task
Deploy the configuration to **$1**:

1. Verify $1 appears in the hosts list above.
2. Check the git status above — warn if uncommitted changes exist.
3. Deploy with the recipe matching the platform:
   - **Darwin** (dungeon, moria, citadel): `just dr $1`
   - **NixOS** (foundation, isengard, home-lab, rohan, mines): `just fr $1`
4. Monitor the deployment and report status.
5. If it fails, suggest the rollback for that platform:
   - **Darwin**: `sudo darwin-rebuild --rollback` — or, since nix-darwin keeps
     generations, `just list-generations` then activate an earlier one.
   - **NixOS**: `sudo nixos-rebuild --rollback switch`

Only deploy the host that was asked for. Never deploy a different host to "check"
something — `just fr home-lab` while working on mines has real consequences.
