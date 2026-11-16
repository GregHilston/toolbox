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
apart by model: `zro/deepseek-v4.1-flash` is Zro (free, $0),
`deepseek/deepseek-v4.1-flash` is Command Code GOAT, `deepseek-v4.1-flash` is Go,
any other `deepseek-*` is the API, and `gpt-*` from the `chatgpt` provider is
Luna on ChatGPT Plus (flat fee, $0). Go and GOAT show list price.
Work that bypasses the gateway shows only in the balance change.
OpenAI Images API spend comes from the ledger `openai-image.py` appends per call.
Above the table, each Go and Luna quota window's reset time, in
New York time with a countdown, from the exporters' resets_at gauges.

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
from zoneinfo import ZoneInfo

PROM = os.environ.get(
    "USAGE_MARK_PROM", "https://grafana.grehg2.xyz/api/datasources/proxy/uid/prometheus/api/v1/query"
)
MARKS = Path(os.environ.get("USAGE_MARK_DIR", Path.home() / ".cache" / "usage-mark"))
PROJECTS = Path(os.environ.get("USAGE_MARK_PROJECTS", Path.home() / ".claude" / "projects"))
WINDOW = int(os.environ.get("USAGE_MARK_WINDOW", 1_000_000))
ROUTES = {"zro/deepseek-v4.1-flash": "Zro", "deepseek/deepseek-v4.1-flash": "GOAT", "deepseek-v4.1-flash": "Go"}
LABELS = ("DS API", "Zro", "GOAT", "Go", "Luna")
FREE = ("Zro", "Luna")
# USD per 1M tokens (cache hit, miss, output) for Flash; peak doubles.
FLASH = {"off": (0.003, 0.15, 0.60), "peak": (0.006, 0.30, 1.20)}
FIELDS = ("in", "out", "cread", "cwrite")
EASTERN = ZoneInfo("America/New_York")
# (gauge prefix, row label, Prometheus window, short name)
RESET_WINDOWS = (
    ("go", "Go", "rolling", "5h"), ("go", "Go", "weekly", "wk"), ("go", "Go", "monthly", "mo"),
    ("luna", "Luna", "5h", "5h"), ("luna", "Luna", "weekly", "wk"),
)  # fmt: skip
IMAGE_LEDGER = Path(os.environ.get("OPENAI_IMAGE_LEDGER", Path.home() / ".cache" / "openai-image" / "ledger.jsonl"))


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


def image_row(ledger: Path, since: float) -> dict | None:
    """Sum OpenAI image calls after `since`; None when there were none."""
    if not ledger.exists():
        return None
    r = {"src": "OpenAI img", "in": 0, "out": 0, "cread": 0, "cwrite": None, "cost": 0.0, "est": False, "images": 0}
    for line in ledger.read_text().splitlines():
        try:
            c = json.loads(line)
        except ValueError:
            continue
        if c["t"] < since:
            continue
        r["in"] += c["text_in"] + c["image_in"]
        r["out"] += c["out"]
        r["cost"] += c["usd"]
        r["images"] += c["n"]
    return r if r["images"] else None


def prom(query: str) -> list[dict]:
    """Run an instant query; raises on transport or API trouble."""
    url = PROM + "?" + urllib.parse.urlencode({"query": query})
    with urllib.request.urlopen(url, timeout=15) as resp:
        body = json.load(resp)
    if body.get("status") != "success":
        raise ValueError(f"prometheus said {body.get('status')}")
    return body["data"]["result"]


def gateway_counters() -> dict[str, dict[str, float]]:
    """Cumulative gateway counters per DeepSeek and ChatGPT model."""
    queries = {
        "total_in": "litellm_input_tokens_metric_total",
        "cread": "litellm_input_cached_tokens_metric_total",
        "out": "litellm_output_tokens_metric_total",
        "spend": "litellm_spend_metric_total",
    }
    out: dict[str, dict[str, float]] = {}
    for key, metric in queries.items():
        for r in prom(f'sum by(model)({metric}{{api_provider=~"deepseek|chatgpt"}})'):
            out.setdefault(r["metric"]["model"], {})[key] = float(r["value"][1])
    return out


def gauges() -> dict[str, float]:
    """Balance, Go and Luna quota percentages right now."""
    out: dict[str, float] = {}
    for r in prom("homelab_deepseek_balance_usd"):
        out["balance"] = float(r["value"][1])
    for r in prom("homelab_opencode_go_usage_percent"):
        out["go_" + r["metric"]["window"]] = float(r["value"][1])
    for r in prom("homelab_chatgpt_usage_percent"):
        out["luna_" + r["metric"]["window"]] = float(r["value"][1])
    for r in prom("homelab_opencode_go_usage_resets_at_seconds"):
        out["go_reset_" + r["metric"]["window"]] = float(r["value"][1])
    for r in prom("homelab_chatgpt_usage_resets_at_seconds"):
        out["luna_reset_" + r["metric"]["window"]] = float(r["value"][1])
    return out


def until(seconds: float) -> str:
    """A countdown as 2w 1d 3h 4m, dropping leading zero units."""
    m = int(seconds // 60)
    parts = [(m // 10080, "w"), (m // 1440 % 7, "d"), (m // 60 % 24, "h"), (m % 60, "m")]
    while len(parts) > 1 and parts[0][0] == 0:
        parts.pop(0)
    return " ".join(f"{n}{u}" for n, u in parts)


def reset_lines(g: dict[str, float], now: float) -> list[str]:
    """When each quota window resets, in Eastern time with a countdown."""
    lines: dict[str, list[str]] = {}
    for prefix, label, window, short_name in RESET_WINDOWS:
        at = g.get(f"{prefix}_reset_{window}")
        if at is None:
            continue
        # Lapsed windows keep their old time.
        when = "reset" if at <= now else dt.datetime.fromtimestamp(at, EASTERN).strftime("%a %b %d %H:%M %Z") + f" ({until(at - now)})"
        lines.setdefault(label, []).append(f"{short_name} {when}")
    return [f"{label} resets: " + " · ".join(parts) for label, parts in lines.items()]


def counter_delta(now: dict[str, dict[str, float]], base: dict[str, dict[str, float]]) -> dict[str, dict[str, float]]:
    """Per-model counter growth; a counter below its baseline reset, so its value is the growth."""
    out: dict[str, dict[str, float]] = {}
    for model, cur in now.items():
        old = base.get(model, {})
        out[model] = {k: (v - old.get(k, 0.0) if v >= old.get(k, 0.0) else v) for k, v in cur.items()}
    return out


def deepseek_rows(delta: dict[str, dict[str, float]], peak: bool) -> dict[str, dict]:
    """Fold gateway deltas into one row per route."""
    rows: dict[str, dict] = {}
    for model, d in delta.items():
        label = "Luna" if model.startswith("gpt-") else ROUTES.get(model, "DS API")
        hit, total, out = d.get("cread", 0.0), d.get("total_in", 0.0), d.get("out", 0.0)
        if not (hit or total or out):
            continue
        r = rows.setdefault(label, {"in": 0, "out": 0, "cread": 0, "cwrite": None, "cost": 0.0, "est": False})
        r["in"] += int(total - hit)
        r["out"] += int(out)
        r["cread"] += int(hit)
        spend = d.get("spend", 0.0)
        if label in FREE:
            spend = 0.0
        elif spend <= 0:  # flat plans: dollars are list price
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
        rows += [{"src": s, "in": None, "out": None, "cread": None, "cwrite": None, "cost": None, "est": False} for s in LABELS]
    else:
        for label in LABELS:
            if label in ds:
                rows.append({"src": label, **ds[label]})
    img = image_row(IMAGE_LEDGER, mark["t"])
    if img:
        rows.append(img)
    extra: dict[str, float | None] = {}
    if now_g is not None and mark.get("gauges"):
        g0 = mark["gauges"]
        extra["balance_change"] = round(now_g["balance"] - g0["balance"], 4) if "balance" in now_g and "balance" in g0 else None
        for w in ("rolling", "weekly", "monthly"):
            extra["go_" + w] = now_g.get("go_" + w)
        for w in ("5h", "weekly"):
            extra["luna_" + w] = now_g.get("luna_" + w)
    now = dt.datetime.now().timestamp()
    resets = reset_lines(now_g, now) if now_g else []
    return {"name": name, "minutes": int(now - mark["t"]) // 60, "rows": rows, "extra": extra, "resets": resets, "notes": notes, "claude_ok": claude is not None}


def shift_lines() -> list[str]:
    """The calling session's context size, and whether its shift still takes work."""
    session = os.environ.get("CLAUDE_CODE_SESSION_ID")
    found = sorted(PROJECTS.glob(f"*/{session}.jsonl")) if session else []
    if not found:
        return []
    import claude_shift

    tokens = claude_shift.context_tokens(found[0])
    window = f"{WINDOW / 1e6:g}M" if WINDOW >= 1_000_000 else f"{WINDOW // 1000}k"
    context = f"Context: {tokens // 1000}k of {window}"
    pane = claude_shift.pane()
    state = claude_shift.load(pane) if pane else None
    if not state:
        return [context, "Shift: not armed; this session never rolls."]
    context += f", drains at {state['threshold'] // 1000}k"
    if state["announced"] != session and tokens < state["threshold"]:
        left = (state["threshold"] - tokens) // 1000
        return [context, f"Shift: taking work, {left}k to the drain (roll {state['rolls']} of {state['max_rolls']})."]
    after = "stopping (roll cap reached)" if state["rolls"] >= state["max_rolls"] else "rolling to a fresh session"
    return [context, f"Shift: draining. Starting nothing new; landing or parking, then {after}."]


def render(rep: dict) -> str:
    """The Markdown table plus its footer lines."""
    shift = rep.get("shift") or []
    above = [*shift, *rep.get("resets", [])]
    lines = [f"**{rep['name']}** +{rep['minutes']}m", "", *above, *([""] if above else []), "| src | in | out | c.read | c.write | $ |", "|---|--:|--:|--:|--:|--:|"]
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
    if x.get("luna_5h") is not None:
        bits.append(f"Luna quota 5h {x['luna_5h']:g}% / wk {x.get('luna_weekly') or 0:g}%")
    if x.get("balance_change") is not None:
        bits.append(f"DS balance {x['balance_change']:+.2f}")
    if bits:
        lines += ["", "; ".join(bits)]
    lines += ["", "Claude counts all repos on this machine; Go and GOAT $ is list-price (~); Zro is free, Luna flat-fee ($0)."]
    imgs = sum(r.get("images", 0) for r in rep["rows"])
    if imgs:
        lines.append(f"OpenAI img: {imgs} images, paid per token on the API.")
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
        notes.append("gateway: no baseline at start")
    else:
        try:
            ds = deepseek_rows(counter_delta(gateway_counters(), mark["counters"]), peak=_peak())
            now_g = gauges()
        except Exception as exc:  # noqa: BLE001
            notes.append(f"gateway unreachable ({exc})")
    rep = build(name, mark, claude, ds, now_g, notes, _peak())
    try:
        rep["shift"] = shift_lines()
    except Exception as exc:  # noqa: BLE001
        rep["notes"].append(f"context unreadable: {exc}")
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
