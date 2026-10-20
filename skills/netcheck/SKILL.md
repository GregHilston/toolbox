---
name: netcheck
description: Triage a network outage from moria, offline-safe and read-only. Use when the internet is down, a network outage, "can't reach" a host or service, DNS is broken, or wifi is down.
license: MIT
---

# Netcheck

One command, already on `PATH`. Run it in your shell (the `terminal` tool in
Hermes, Bash in Claude Code, `bash` in pi) exactly as shown: no `python3` in
front and no directory. It works with the internet down.

```bash
netcheck
netcheck --json
```

It walks the ladder (link, router, dungeon, internet, DNS, local DNS, Tailscale,
services), stops at the first failing layer, and prints `VERDICT:`, `next:` and a
`works:` line saying what you can still use, such as the local model.

1. Run `netcheck` first. Do not guess the cause before it answers.
2. Open the runbook section it names in `next:` and follow it step by step.
3. Run `netcheck` again after each step Greg approves.

Read-only: do not restart the router, a switch, dungeon, dnsmasq or Tailscale, and
do not change DNS or Omada settings, without Greg saying so. Do not use `nmap` or
web search to diagnose; with the internet down they tell you nothing.
