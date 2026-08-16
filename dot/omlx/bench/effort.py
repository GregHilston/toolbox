#!/usr/bin/env python3
"""
Measure the cost of Qwen3.8's reasoning_effort levels.

The chat template defaults reasoning_effort to 'xhigh' (chat_template.jinja:47),
so an unconfigured Qwen3.8 spends the maximum on thinking for every request.
This measures how many tokens each level actually burns, and the wall-clock to a
finished answer -- which is what latency feels like, not raw tok/s.
"""
import json, sys, time, urllib.request, os, statistics

BASE = "http://127.0.0.1:8000/v1"
HERE = os.path.dirname(os.path.abspath(__file__))
KEY = open(os.path.join(HERE, "omlx_key")).read().strip()
MODEL = sys.argv[1] if len(sys.argv) > 1 else "Qwen3.8-27B-4bit"

PROMPT = (
    "A Python service intermittently returns stale data. It runs 4 gunicorn workers, "
    "each with an in-process dict cache keyed by user id, invalidated on write. "
    "Writes go through a single Postgres primary. Diagnose the most likely root cause "
    "and give the two smallest correct fixes."
)


def once(effort, enable_thinking=True, max_tokens=8000):
    body = {
        "model": MODEL,
        "messages": [{"role": "user", "content": PROMPT}],
        "max_tokens": max_tokens,
        "temperature": 1.0, "top_p": 0.95, "top_k": 20,
    }
    kw = {}
    if effort is not None:
        kw["reasoning_effort"] = effort
    if not enable_thinking:
        kw["enable_thinking"] = False
    if kw:
        body["chat_template_kwargs"] = kw
    req = urllib.request.Request(
        f"{BASE}/chat/completions", data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"},
    )
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=1800) as r:
        d = json.load(r)
    wall = time.perf_counter() - t0
    msg = d["choices"][0]["message"]
    u = d.get("usage", {})
    think = msg.get("reasoning_content") or ""
    ans = msg.get("content") or ""
    return {
        "effort": effort if effort else ("no-think" if not enable_thinking else "default"),
        "wall": wall,
        "completion_tokens": u.get("completion_tokens"),
        "think_chars": len(think),
        "answer_chars": len(ans),
        "finish": d["choices"][0].get("finish_reason"),
        "tps": (u.get("completion_tokens") or 0) / wall,
    }


if __name__ == "__main__":
    print(f"model={MODEL}\n")
    rows = []
    trials = [
        (None, True),        # template default (= xhigh)
        ("low", True),
        ("medium", True),
        ("xhigh", True),
        (None, False),       # thinking disabled
    ]
    for effort, think in trials:
        try:
            r = once(effort, think)
            rows.append(r)
            print(
                f"  {r['effort']:9s} | {r['completion_tokens']:6} tok | {r['wall']:7.1f}s "
                f"| {r['tps']:5.1f} t/s | think {r['think_chars']:6} ch | ans {r['answer_chars']:5} ch "
                f"| {r['finish']}",
                flush=True,
            )
        except Exception as e:
            print(f"  {str(effort):9s} FAILED {type(e).__name__}: {e}", flush=True)
    json.dump(rows, open(os.path.join(HERE, "effort.json"), "w"), indent=2)
