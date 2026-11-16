#!/usr/bin/env python3
"""Tell an armed orchestrator to drain once its context passes the shift limit. A Claude Code Stop hook.

Opt-in: does nothing unless `shift-arm` armed this Herdr pane. On an armed
pane it records every stop and how many background tasks and crons are still
live, which the roll worker waits on, since /clear kills them. It blocks the
stop once per drain, with a reason that tells the model to wind down and run
`orchestrator-roll`; the worker re-opens the drain after each /clear or failed
roll. Greg won't use auto-compact; this replaces it. Runs every turn, so it
reads only the transcript's tail. Any error lets the stop through.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(os.environ.get("TOOLBOX_HOME") or Path.home() / "Git/toolbox") / "bin"))
import claude_shift  # noqa: E402


def reason(tokens: int, state: dict) -> str:
    rolls, cap = state["rolls"], state["max_rolls"]
    text = (
        f"Shift drain: this session's context is {tokens // 1000}k tokens, past this pane's "
        f"{state['threshold'] // 1000}k shift limit. Wind the shift down now. Start no new "
        "tickets. Finish and land, or park, all in-flight work, and let every background "
        "subagent, Monitor, cron and Bash job end: /clear kills them, and the roll waits until "
        "none is left. A subagent's `until grep` wait loop or an artifact Monitor outlives it, "
        "so TaskStop every leftover one.Write lessons to the repo docs and each ticket's status to its ticket; "
        "the fresh session reads only those. File a ticket for every bug, follow-up or "
        "unfinished piece this shift found, and split any blocked ticket whose build needs no "
        "Greg into its own ready ticket. Then run `orchestrator-roll` and end your turn; it "
        "clears this session once idle and restarts it with the fixed prompt. The pane stays "
        "armed across the roll (`shift-arm` keeps the count if run again). Only if, after "
        "that filing, every open milestone ticket needs Greg, send one Pushover listing them "
        "(`pushover.py -m '...'`) and stop instead of rolling."
    )
    if rolls >= cap:
        text += (
            f" This pane has used all {cap} rolls, so `orchestrator-roll` will refuse: after "
            "draining, send one Pushover saying the shift limit is reached, and stop."
        )
    return text


def busy(event: dict) -> int:
    tasks, crons = event.get("background_tasks"), event.get("session_crons")
    if tasks is None or crons is None:
        return -1  # registry unreachable: assume live work
    return len(tasks) + len(crons)


def main() -> int:
    pane = claude_shift.pane()
    if not pane or not claude_shift.state_path(pane).exists():
        return 0
    event = json.load(sys.stdin)
    with claude_shift.locked(pane):
        try:
            state = claude_shift.load(pane)
        except claude_shift.Invalid as e:
            claude_shift.quarantine(pane, e)
            return 0
        if not state:
            return 0
        state["stops"] += 1
        state["busy"] = busy(event)
        session = event.get("session_id")
        block = None
        if not event.get("stop_hook_active") and state["announced"] != session:
            tokens = claude_shift.context_tokens(event["transcript_path"])
            if tokens >= state["threshold"]:
                state["announced"], state["tokens"] = session, tokens
                block = reason(tokens, state)
        claude_shift.save(pane, state)
    if block:
        print(json.dumps({"decision": "block", "reason": block}))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # never block on the hook's own failure
        sys.exit(0)
