#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Mark a moment, then report LLM token use and cost since it, as a tiny table.

    usage-mark.py start <name>          record a baseline
    usage-mark.py report <name> [--json]  delta since the baseline

Claude tokens come from every transcript under ~/.claude/projects on this
machine, all repos included (Claude is on a subscription, so cost shows "-").
DeepSeek API and OpenCode Go come from the LiteLLM gateway's counters in
Prometheus, read through Grafana's datasource proxy. The gateway tells them
apart by model: `deepseek-v4.1-flash` is Go, any other `deepseek-*` is the API.
Work that bypasses the gateway shows only in the balance change.

Columns: in is fresh input (DeepSeek cache misses), c.read is cache hits,
c.write is Claude's cache creation. A source that cannot answer prints `?`
and one reason line; the exit code stays 0.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path

PROM = os.environ.get(
    "USAGE_MARK_PROM", "https://grafana.grehg2.xyz/api/datasources/proxy/uid/prometheus/api/v1/query"
)
MARKS = Path(os.environ.get("USAGE_MARK_DIR", Path.home() / ".cache" / "usage-mark"))
PROJECTS = Path(os.environ.get("USAGE_MARK_PROJECTS", Path.home() / ".claude" / "projects"))
GO_MODEL = "deepseek-v4.1-flash"
# USD per 1M tokens (cache hit, miss, output) for Flash; peak doubles.
FLASH = {"off": (0.003, 0.15, 0.60), "peak": (0.006, 0.30, 1.20)}
FIELDS = ("in", "out", "cread", "cwrite")


def parse_ts(text: str) -> float:
    """Epoch seconds from a transcript's ISO timestamp."""
    return dt.datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp()


def claude_usage(root: Path, since: float) -> dict[str, dict[str, int]]:
    """Sum message usage by model for entries after `since`.

    Claude Code writes a streamed message as several lines sharing one id, so the
    last usage seen per id wins, across the main and subagent transcripts alike.
    """
    seen: dict[str, tuple[str, dict]] = {}
    for path in root.rglob("*.jsonl"):
        if path.stat().st_mtime < since:
            continue
        with path.open(errors="replace") as fh:
            for line in fh:
                if '"usage"' not in line:
                    continue
                try:
                    row = json.loads(line)
                    msg = row["message"]
                    if parse_ts(row["timestamp"]) < since or not msg.get("id"):
                        continue
                    seen[msg["id"]] = (msg.get("model") or "?", msg["usage"])
                except (ValueError, KeyError, TypeError):
                    continue
    out: dict[str, dict[str, int]] = {}
    for model, u in seen.values():
        if model.startswith("<"):
            continue
        row = out.setdefault(model, dict.fromkeys(FIELDS, 0))
        row["in"] += u.get("input_tokens") or 0
        row["out"] += u.get("output_tokens") or 0
        row["cread"] += u.get("cache_read_input_tokens") or 0
        row["cwrite"] += u.get("cache_creation_input_tokens") or 0
    return out


def prom(query: str) -> list[dict]:
    """Run an instant query; raises on transport or API trouble."""
    url = PROM + "?" + urllib.parse.urlencode({"query": query})
    with urllib.request.urlopen(url, timeout=15) as resp:
        body = json.load(resp)
    if body.get("status") != "success":
        raise ValueError(f"prometheus said {body.get('status')}")
    return body["data"]["result"]


def gateway_counters() -> dict[str, dict[str, float]]:
    """Cumulative gateway counters per deepseek model."""
    queries = {
        "total_in": "litellm_input_tokens_metric_total",
        "cread": "litellm_input_cached_tokens_metric_total",
        "out": "litellm_output_tokens_metric_total",
        "spend": "litellm_spend_metric_total",
    }
    out: dict[str, dict[str, float]] = {}
    for key, metric in queries.items():
        for r in prom(f'sum by(model)({metric}{{api_provider="deepseek"}})'):
            out.setdefault(r["metric"]["model"], {})[key] = float(r["value"][1])
    return out


def gauges() -> dict[str, float]:
    """Balance and Go quota percentages right now."""
    out: dict[str, float] = {}
    for r in prom("homelab_deepseek_balance_usd"):
        out["balance"] = float(r["value"][1])
    for r in prom("homelab_opencode_go_usage_percent"):
        out["go_" + r["metric"]["window"]] = float(r["value"][1])
    return out


def counter_delta(now: dict[str, dict[str, float]], base: dict[str, dict[str, float]]) -> dict[str, dict[str, float]]:
    """Per-model counter growth; a counter below its baseline reset, so its value is the growth."""
    out: dict[str, dict[str, float]] = {}
    for model, cur in now.items():
        old = base.get(model, {})
        out[model] = {k: (v - old.get(k, 0.0) if v >= old.get(k, 0.0) else v) for k, v in cur.items()}
    return out


def deepseek_rows(delta: dict[str, dict[str, float]], peak: bool) -> dict[str, dict]:
    """Fold gateway deltas into a `DS API` row and a `Go` row."""
    rows: dict[str, dict] = {}
    for model, d in delta.items():
        label = "Go" if model == GO_MODEL else "DS API"
        hit, total, out = d.get("cread", 0.0), d.get("total_in", 0.0), d.get("out", 0.0)
        if not (hit or total or out):
            continue
        r = rows.setdefault(label, {"in": 0, "out": 0, "cread": 0, "cwrite": None, "cost": 0.0, "est": False})
        r["in"] += int(total - hit)
        r["out"] += int(out)
        r["cread"] += int(hit)
        spend = d.get("spend", 0.0)
        if spend <= 0:  # Go bills a flat plan, so its dollars are list price
            rate = FLASH["peak" if peak else "off"]
            spend = (hit * rate[0] + (total - hit) * rate[1] + out * rate[2]) / 1e6
            r["est"] = True
        r["cost"] += spend
    return rows


def short(model: str) -> str:
    """A phone-width Claude model name."""
    return model.removeprefix("claude-")


def fmt(n: int | None) -> str:
    """Tokens as 1.2k / 3.4M; None as `?`."""
    if n is None:
        return "?"
    for limit, suffix in ((1e9, "G"), (1e6, "M"), (1e3, "k")):
        if n >= limit:
            return f"{n / limit:.1f}{suffix}"
    return str(n)


def build(name: str, mark: dict, claude: dict | None, ds: dict | None, now_g: dict | None, notes: list[str], peak: bool) -> dict:
    """Assemble the report as plain data."""
    rows = []
    for model, v in sorted((claude or {}).items(), key=lambda kv: -kv[1]["out"]):
        rows.append({"src": short(model), "in": v["in"], "out": v["out"], "cread": v["cread"], "cwrite": v["cwrite"], "cost": None, "est": False})
    if ds is None:
        rows += [{"src": s, "in": None, "out": None, "cread": None, "cwrite": None, "cost": None, "est": False} for s in ("DS API", "Go")]
    else:
        for label in ("DS API", "Go"):
            if label in ds:
                rows.append({"src": label, **ds[label]})
    extra: dict[str, float | None] = {}
    if now_g is not None and mark.get("gauges"):
        g0 = mark["gauges"]
        extra["balance_change"] = round(now_g["balance"] - g0["balance"], 4) if "balance" in now_g and "balance" in g0 else None
        for w in ("rolling", "weekly", "monthly"):
            extra["go_" + w] = now_g.get("go_" + w)
    elapsed = int(dt.datetime.now().timestamp() - mark["t"])
    return {"name": name, "minutes": elapsed // 60, "rows": rows, "extra": extra, "notes": notes, "claude_ok": claude is not None}


def render(rep: dict) -> str:
    """The Markdown table plus its footer lines."""
    lines = [f"**{rep['name']}** +{rep['minutes']}m", "", "| src | in | out | c.read | c.write | $ |", "|---|--:|--:|--:|--:|--:|"]
    for r in rep["rows"]:
        cost = "-" if r["cost"] is None else ("?" if r["cost"] == "?" else f"{'~' if r['est'] else ''}{r['cost']:.2f}")
        if r["in"] is None:
            cost = "?"
        cw = "-" if r["cwrite"] is None and r["in"] is not None else fmt(r["cwrite"])
        lines.append(f"| {r['src']} | {fmt(r['in'])} | {fmt(r['out'])} | {fmt(r['cread'])} | {cw} | {cost} |")
    x = rep["extra"]
    bits = []
    if x.get("go_rolling") is not None:
        bits.append(f"Go quota 5h {x['go_rolling']:g}% / wk {x['go_weekly']:g}% / mo {x['go_monthly']:g}%")
    if x.get("balance_change") is not None:
        bits.append(f"DS balance {x['balance_change']:+.2f}")
    if bits:
        lines += ["", "; ".join(bits)]
    lines += ["", "Claude counts all repos on this machine; Go $ is list-price (~)."]
    lines += [f"? {n}" for n in rep["notes"]]
    return "\n".join(lines)


def start(name: str) -> int:
    """Write the baseline."""
    mark: dict = {"t": dt.datetime.now().timestamp(), "counters": None, "gauges": None}
    notes = []
    try:
        mark["counters"], mark["gauges"] = gateway_counters(), gauges()
    except Exception as exc:  # noqa: BLE001 - a dead gateway must not block the mark
        notes.append(f"gateway baseline missing: {exc}")
    MARKS.mkdir(parents=True, exist_ok=True)
    (MARKS / f"{name}.json").write_text(json.dumps(mark))
    print(f"marked {name}" + "".join(f"\n? {n}" for n in notes))
    return 0


def report(name: str, as_json: bool) -> int:
    """Print the delta since the baseline."""
    path = MARKS / f"{name}.json"
    if not path.exists():
        print(f"? no mark named {name}; run `usage-mark.py start {name}`")
        return 0
    mark = json.loads(path.read_text())
    notes: list[str] = []
    try:
        claude = claude_usage(PROJECTS, mark["t"])
    except Exception as exc:  # noqa: BLE001
        claude = None
        notes.append(f"Claude transcripts unreadable: {exc}")
    ds = now_g = None
    if mark.get("counters") is None:
        notes.append("DeepSeek/Go: no gateway baseline at start")
    else:
        try:
            ds = deepseek_rows(counter_delta(gateway_counters(), mark["counters"]), peak=_peak())
            now_g = gauges()
        except Exception as exc:  # noqa: BLE001
            notes.append(f"DeepSeek/Go: gateway unreachable ({exc})")
    rep = build(name, mark, claude, ds, now_g, notes, _peak())
    print(json.dumps(rep, indent=2) if as_json else render(rep))
    return 0


def _peak() -> bool:
    """DeepSeek's double-price window: 01-04 and 06-10 UTC, Monday to Friday."""
    u = dt.datetime.now(dt.timezone.utc)
    return u.weekday() < 5 and any(a <= u.hour < b for a, b in ((1, 4), (6, 10)))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("action", choices=("start", "report"))
    ap.add_argument("name")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    return start(a.name) if a.action == "start" else report(a.name, a.json)


if __name__ == "__main__":
    sys.exit(main())
