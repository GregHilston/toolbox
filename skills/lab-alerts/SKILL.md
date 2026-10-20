---
name: lab-alerts
description: List the home lab's recent and currently firing alerts, then diagnose them from the runbooks. Use for "recent alerts", "what's alerting", "what fired", "why did I get a Pushover", "is X down", or "what's been alerting lately?". Run it before any other lab check.
license: MIT
---

# Lab alerts

Run this in your shell (the `terminal` tool in Hermes, Bash in Claude Code,
`bash` in pi) exactly as shown, with no `python3` in front and no directory.
Do not use web search instead.

```bash
lab-alerts.py              # firing now, plus the last 3 days of history
lab-alerts.py --days 7     # a longer history
lab-alerts.py --json       # the same, as JSON
```

`OPEN` means no all-clear has arrived. Some alerts never send one, so check
whether the thing is still broken.
Each open item prints its log command; run it as shown.

**If Greg asked what is alerting** ("recent alerts", "what's alerting"), answer
from this output alone: group the alerts, name each group's runbook, and ask
which one to dig into. Run nothing else.

**If he asked about one alert** ("why did I get…", "is X down"):

1. Find its runbook in `~/Git/home-lab/docs/runbooks/`. `README.md` is the
   index and the output often names the runbook slug. `docs/alerting.md`
   explains where alerts come from.
2. Run the read-only checks the runbook lists to see if the fault is still real.
3. Report what is wrong, the likely cause, and the fix the runbook gives.
   Propose the fix and wait: do not restart, edit or delete anything.
   Stop and report after five commands, even if unsure; Greg can ask for more.

If several alerts fire at once, look for one shared cause first (NFS, Unraid,
power, Caddy). Only call alerts related when LIKELY SHARED CAUSE says so; say the
rest are separate or unknown.

For one named alert use the home-lab `oncall` skill. Use `triage`, a full
sweep, only when Greg asks for one.
