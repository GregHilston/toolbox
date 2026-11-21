#!/usr/bin/env python3
"""Print an XO alert when DeepSeek is used while the fleet switch is on.

The switch is ~/.config/fleet/no-deepseek (override: $NO_DEEPSEEK_FILE). The
control loop (control-loop.sh) runs this each pass and deduplicates hourly.
It prints nothing when the file is absent, no requests rose in the last 15
min, or Prometheus cannot be read.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

BIN = Path(__file__).resolve().parent
QUERY = ('sum by (user_agent, client_ip) '
         '(increase(litellm_proxy_total_requests_metric_total{requested_model=~".*deepseek.*"}[15m]))')


def load(name: str, file: str):
    spec = importlib.util.spec_from_file_location(name, BIN / file)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def alert(rows: list[dict], reason: str) -> str | None:
    """rows: Prometheus instant-vector results."""
    counted = [(float(r["value"][1]), r["metric"]) for r in rows]
    total = sum(n for n, _ in counted)
    if total < 1:
        return None
    n, top = max(counted, key=lambda c: c[0])
    return (f"XO deepseek: {total:.0f} requests in 15 min under no-deepseek ({reason}); "
            f"top caller user_agent={top.get('user_agent', '?')} client_ip={top.get('client_ip', '?')} ({n:.0f})")


def main(fetch=None) -> int:
    preflight = load("_preflight", "deepseek-preflight.py")
    f = preflight.no_deepseek_file()
    if not f.exists():
        return 0
    reason = f.read_text().strip() or "no reason given"
    try:
        rows = (fetch or load("_usage_mark", "usage-mark.py").prom)(QUERY)
        line = alert(rows, reason)
    except Exception:
        return 0
    if line:
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
