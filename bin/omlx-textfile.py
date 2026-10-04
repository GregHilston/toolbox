#!/usr/bin/env python3
"""Write oMLX's loaded models and load for node_exporter's textfile collector.

Asks each oMLX server which models sit in memory, how much they take against the
ceiling, and how busy it is. One run covers dungeon and moria, so the LLM Gateway
dashboard shows both. A sleeping moria writes omlx_up 0 and nothing else.

The label is `server`, not `host`: Prometheus already sets host="dungeon" on
everything node_exporter serves, and a clash would rename ours to exported_host.

    omlx-textfile.py    write $NODE_EXPORTER_TEXTFILE_DIR/omlx.prom; run every 60s
"""

from __future__ import annotations

import json
import os
import urllib.request
from pathlib import Path

SERVERS = {"dungeon": "http://localhost:8000", "moria": "http://100.115.155.85:8000"}
TIMEOUT = 3


def esc(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def fetch(base: str, path: str, key: str) -> dict:
    req = urllib.request.Request(base + path, headers={"Authorization": f"Bearer {key}"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return json.load(r)


def render(results: dict[str, tuple[dict, dict] | None]) -> str:
    """results maps server -> (/api/status, /v1/models/status), or None if unreachable."""
    gauges = {
        "omlx_up": "1 if the server answered this run.",
        "omlx_model_loaded": "1 if the model is in memory. Profiles are folded into their base model.",
        "omlx_model_memory_bytes": "Memory the loaded model holds.",
        "omlx_model_last_access_timestamp_seconds": "When the model last served a request.",
        "omlx_memory_used_bytes": "Memory held by all loaded models.",
        "omlx_memory_max_bytes": "oMLX's model memory ceiling.",
        "omlx_active_requests": "Requests being generated now.",
        "omlx_waiting_requests": "Requests queued behind them.",
        "omlx_generation_tokens_per_second": "Average decode speed since oMLX started.",
        "omlx_prefill_tokens_per_second": "Average prefill speed since oMLX started.",
    }
    counters = {
        "omlx_requests_total": "Requests served since oMLX started.",
        "omlx_prompt_tokens_total": "Prompt tokens since oMLX started.",
        "omlx_completion_tokens_total": "Completion tokens since oMLX started.",
        "omlx_cached_tokens_total": "Prompt tokens served from the prefix cache.",
    }
    rows: dict[str, list[str]] = {name: [] for name in [*gauges, *counters]}

    for server, result in results.items():
        s = f'server="{esc(server)}"'
        rows["omlx_up"].append(f"omlx_up{{{s}}} {0 if result is None else 1}")
        if result is None:
            continue
        status, models = result
        for metric, field in [
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
        ]:
            if status.get(field) is not None:
                rows[metric].append(f"{metric}{{{s}}} {status[field]}")
        for m in models.get("models", []):
            # A profile (`model:lab`) shares its base model's weights.
            if m.get("source_model_id"):
                continue
            labels = f'{s},model="{esc(m["id"])}"'
            loaded = bool(m.get("loaded"))
            rows["omlx_model_loaded"].append(f"omlx_model_loaded{{{labels}}} {int(loaded)}")
            if loaded:
                size = m.get("resident_estimated_size") or m.get("estimated_size") or 0
                rows["omlx_model_memory_bytes"].append(f"omlx_model_memory_bytes{{{labels}}} {size}")
            if m.get("last_access"):
                rows["omlx_model_last_access_timestamp_seconds"].append(
                    f"omlx_model_last_access_timestamp_seconds{{{labels}}} {m['last_access']}"
                )

    out = []
    for name, lines in rows.items():
        if not lines:
            continue
        kind = "gauge" if name in gauges else "counter"
        out += [f"# HELP {name} {gauges.get(name) or counters[name]}", f"# TYPE {name} {kind}", *lines]
    return "\n".join(out) + "\n"


def main() -> None:
    settings = json.loads((Path.home() / ".omlx" / "settings.json").read_text())
    key = settings["auth"]["api_key"]
    results: dict[str, tuple[dict, dict] | None] = {}
    for server, base in SERVERS.items():
        try:
            results[server] = (fetch(base, "/api/status", key), fetch(base, "/v1/models/status", key))
        except (OSError, ValueError):
            results[server] = None

    out_dir = Path(os.environ.get("NODE_EXPORTER_TEXTFILE_DIR") or Path.home() / ".local/state/node_exporter")
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "omlx.prom"
    tmp = out.with_name(f"omlx.prom.{os.getpid()}")
    tmp.write_text(render(results))
    tmp.replace(out)


if __name__ == "__main__":
    main()
