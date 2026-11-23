#!/usr/bin/env python3
"""xo-goal.py LOG STAMP: hourly nudge until a goal tick."""

from __future__ import annotations

import re
import sys
import time
from datetime import datetime
from pathlib import Path

HOUR = 3600


def main() -> int:
    log, stamp = Path(sys.argv[1]), Path(sys.argv[2])
    try:
        text = log.read_text()
    except OSError:
        return 0
    goal = re.search(r"^## Goal[ \t]*\n(.*?)(?=^## |\Z)", text, re.S | re.M)
    if not goal or not goal.group(1).strip():
        return 0
    now = time.time()
    ticks = re.findall(r"^### (\d{4}-\d\d-\d\d \d\d:\d\d) goal tick", text, re.M)
    if ticks and now - max(datetime.strptime(t, "%Y-%m-%d %H:%M").timestamp() for t in ticks) < HOUR:
        return 0
    if stamp.exists() and now - stamp.stat().st_mtime < HOUR:
        return 0
    stamp.touch()
    first = goal.group(1).strip().splitlines()[0][:200]
    print(f"XO goal: no goal tick in the last hour. Goal: {first} Do the tick in ## Goal, then journal "
          f"'### <date> goal tick' with its numbers.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
