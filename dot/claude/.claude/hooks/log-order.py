#!/usr/bin/env python3
"""Append each prompt a commander receives to its run log. A Claude Code UserPromptSubmit hook.

Acts only on a pane whose shift state has a `log` key (`shift-arm --log`).
Orders then survive a roll in the file, not in the chat. Never blocks.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(os.environ.get("TOOLBOX_HOME") or Path.home() / "Git/toolbox") / "bin"))
import claude_shift  # noqa: E402


def main() -> None:
    pane = claude_shift.pane()
    if not pane:
        return
    # unlocked: shift-arm replaces the file atomically
    state = json.loads(claude_shift.state_path(pane).read_text())
    log = state.get("log")
    if not log:
        return
    prompt = json.load(sys.stdin).get("prompt") or ""
    who = "restart" if prompt == state.get("prompt") else "XO" if prompt.startswith("XO:") else "Greg"
    with open(log, "a") as f:
        f.write(f"\n### {datetime.now():%Y-%m-%d %H:%M} {who}\n\n{prompt}\n")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
