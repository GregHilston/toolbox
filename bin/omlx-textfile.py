#!/usr/bin/env python3
"""Write oMLX's loaded models and load for node_exporter's textfile collector.

Asks each oMLX server which models sit in memory, how much they take against the
ceiling, and how busy it is. One run covers dungeon, moria and citadel, so the LLM
Gateway dashboard shows all three. A sleeping laptop writes omlx_up 0 and nothing else.

The label is `server`, not `host`: Prometheus already sets host="dungeon" on
everything node_exporter serves, and a clash would rename ours to exported_host.

    omlx-textfile.py    write $NODE_EXPORTER_TEXTFILE_DIR/omlx.prom; run every 60s
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

SERVERS = {
    "dungeon": "http://localhost:8000",
    "moria": "http://100.115.155.85:8000",
    "citadel": "http://100.93.190.106:8000",
}
# Short for laptops that sleep; dungeon may be mid-prefill.
TIMEOUT = {"dungeon": 10}
REMOTE_TIMEOUT = 3

GAUGES = {
    "omlx_up": "1 if the server answered this run.",
    "omlx_model_loaded": "1 if the model is in memory. Profiles are folded into their base model.",
    "omlx_model_loading": "1 while the model is being loaded.",
    "omlx_model_memory_bytes": "Memory the loaded model holds.",
    "omlx_model_last_access_timestamp_seconds": "When the model last served a request.",
    "omlx_memory_used_bytes": "Memory held by all loaded models.",
    "omlx_memory_max_bytes": "oMLX's model memory ceiling.",
    "omlx_active_requests": "Requests being generated now.",
    "omlx_waiting_requests": "Requests queued behind them.",
    "omlx_generation_tokens_per_second": "Average decode speed since oMLX started.",
    "omlx_prefill_tokens_per_second": "Average prefill speed since oMLX started.",
}
COUNTERS = {
    "omlx_requests_total": "Requests served since oMLX started.",
    "omlx_prompt_tokens_total": "Prompt tokens since oMLX started.",
    "omlx_completion_tokens_total": "Completion tokens since oMLX started.",
    "omlx_cached_tokens_total": "Prompt tokens served from the prefix cache.",
}
STATUS_FIELDS = [
    ("omlx_memory_used_bytes", "model_memory_used"),
    ("omlx_memory_max_bytes", "model_memory_max"),
    ("omlx_active_requests", "active_requests"),
    ("omlx_waiting_requests", "waiting_requests"),
    ("omlx_generation_tokens_per_second", "avg_generation_tps"),
    ("omlx_prefill_tokens_per_second", "avg_prefill_tps"),
    ("omlx_requests_total", "total_requests"),
    ("omlx_prompt_tokens_total", "total_prompt_tokens"),
    ("omlx_completion_tokens_total", "total_completion_tokens"),
    ("omlx_cached_tokens_total", "total_cached_tokens"),
]


def esc(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def num(value: object) -> int | float | None:
    # One non-number makes node_exporter drop the whole file.
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return value


def fetch(base: str, path: str, key: str, timeout: float) -> dict:
    req = urllib.request.Request(base + path, headers={"Authorization": f"Bearer {key}"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def server_lines(server: str, status: dict, models: dict) -> list[tuple[str, str]]:
    """(metric, line) pairs for one server that answered. Raises on an unexpected shape."""
    s = f'server="{esc(server)}"'
    rows = [("omlx_up", f"omlx_up{{{s}}} 1")]
    for metric, field in STATUS_FIELDS:
        if (v := num(status.get(field))) is not None:
            rows.append((metric, f"{metric}{{{s}}} {v}"))
    for m in models["models"]:
        # A profile (`model:lab`) shares its base model's weights.
        if m.get("source_model_id"):
            continue
        labels = f'{s},model="{esc(str(m["id"]))}"'
        loaded = m.get("loaded") is True
        rows.append(("omlx_model_loaded", f"omlx_model_loaded{{{labels}}} {int(loaded)}"))
        rows.append(("omlx_model_loading", f"omlx_model_loading{{{labels}}} {int(m.get('is_loading') is True)}"))
        size = num(m.get("resident_estimated_size")) or num(m.get("estimated_size"))
        if loaded and size is not None:
            rows.append(("omlx_model_memory_bytes", f"omlx_model_memory_bytes{{{labels}}} {size}"))
        if (last := num(m.get("last_access"))) is not None:
            rows.append(("omlx_model_last_access_timestamp_seconds",
                         f"omlx_model_last_access_timestamp_seconds{{{labels}}} {last}"))
    return rows


def render(results: dict[str, list[tuple[str, str]] | None]) -> str:
    """results maps server -> server_lines(), or None if it did not answer usefully."""
    by_metric: dict[str, list[str]] = {name: [] for name in [*GAUGES, *COUNTERS]}
    for server, rows in results.items():
        for metric, line in rows if rows is not None else [("omlx_up", f'omlx_up{{server="{esc(server)}"}} 0')]:
            by_metric[metric].append(line)
    out = []
    for name, lines in by_metric.items():
        if lines:
            kind = "gauge" if name in GAUGES else "counter"
            out += [f"# HELP {name} {GAUGES.get(name) or COUNTERS[name]}", f"# TYPE {name} {kind}", *lines]
    return "\n".join(out) + "\n"


def quiet(err: Exception) -> bool:
    """A sleeping or absent host: normal, so not worth a log line every minute."""
    return isinstance(err, OSError) and not isinstance(err, urllib.error.HTTPError)


def collect() -> dict[str, list[tuple[str, str]] | None]:
    results: dict[str, list[tuple[str, str]] | None] = dict.fromkeys(SERVERS)
    try:
        key = json.loads((Path.home() / ".omlx" / "settings.json").read_text())["auth"]["api_key"]
    except Exception as e:
        print(f"settings: {type(e).__name__}: {e}", file=sys.stderr)
        return results
    for server, base in SERVERS.items():
        timeout = TIMEOUT.get(server, REMOTE_TIMEOUT)
        try:
            status = fetch(base, "/api/status", key, timeout)
            results[server] = server_lines(server, status, fetch(base, "/v1/models/status", key, timeout))
        except Exception as e:
            if not quiet(e):
                print(f"{server}: {type(e).__name__}: {e}", file=sys.stderr)
    return results


def main() -> None:
    out_dir = Path(os.environ.get("NODE_EXPORTER_TEXTFILE_DIR") or Path.home() / ".local/state/node_exporter")
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "omlx.prom"
    tmp = out.with_name(f"omlx.prom.{os.getpid()}")
    try:
        tmp.write_text(render(collect()))
        tmp.replace(out)
    finally:
        tmp.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
