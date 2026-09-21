#!/usr/bin/env python3
"""Summarise one run's model traffic from oMLX's log.

Not from `~/.omlx/stats.json`. That file flushes lazily and the lag is
unbounded: during run `smoke-enriched` it sat at 1240 requests while the log
showed eleven completions in the previous six minutes. Everything built on the
counter inherited that — a stall detector reading it would have paged on a
healthy run, and `agent-verify.sh` reported "the builder served NO requests"
twice about a builder that was serving them.

The log line is timestamped, names the model, and carries the token counts, so
it answers the question directly. Full dates are compared rather than clock
times so a run crossing midnight still works.

Snake_case and underscore-prefixed because `bin/**` is on $PATH recursively and
this is a helper for `agent-iterate.sh`, not a command anyone runs.
"""

from __future__ import annotations

import re
import sys

LINE = re.compile(
    r"^(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d),\d+ .*"
    r"Chat completion: model=([^,]+), (\d+) tokens in ([\d.]+)s .*prompt: (\d+)"
)


def main() -> int:
    log, stamp, *models = sys.argv[1:]
    agg = {m: [0, 0, 0, 0.0] for m in models}
    try:
        with open(log, errors="ignore") as fh:
            for line in fh:
                m = LINE.match(line)
                if m and m.group(1) >= stamp and m.group(2) in agg:
                    a = agg[m.group(2)]
                    a[0] += 1
                    a[1] += int(m.group(5))
                    a[2] += int(m.group(3))
                    a[3] += float(m.group(4))
    except OSError:
        pass

    parts = []
    for name in models:
        n, prompt, completion, secs = agg[name]
        parts.append(
            f"{name}: {n} reqs, {prompt // n}/{completion // n} prompt/completion tok per req, "
            f"{secs:.0f}s of model time" if n else f"{name}: 0 reqs"
        )
    print("<br>".join(parts), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
