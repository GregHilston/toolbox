---
description: Test NixOS configuration without switching
allowed-tools: Bash(just:*), Bash(cd:*), Bash(ls:*)
argument-hint: [hostname]
---

## Available Hosts
!`ls -1 /home/ghilston/Git/toolbox/nixos/hosts/pcs/ /home/ghilston/Git/toolbox/nixos/hosts/vms/ 2>/dev/null | grep -v ':' | grep -v '^$'`

## Current Changes
!`cd /home/ghilston/Git/toolbox/nixos && git diff --stat HEAD || echo "No changes"`

## Task
Test NixOS configuration for **$1** without deploying:

1. Verify $1 is valid (must be in hosts list above)
2. Run: `cd /home/ghilston/Git/toolbox/nixos && just ft $1`
3. Monitor for errors/warnings
4. Report results and suggest fixes if build fails

Do NOT deploy - this is test-only.
