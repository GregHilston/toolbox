#!/usr/bin/env python3
"""
Lightning MTP on vs off for one checkpoint, sampled alternately so drift cancels.

Needs two model ids for the same weights, one with "mtp_enabled": true in
model_settings.json and one without. Make the second a symlinked twin dir
(e.g. <dir>-nomtp) with its own entry; docs/model-evaluation.md, step 5.

    mtp_paired.py <mtp-off-id> <mtp-on-id> [--rounds 6] [--max-tokens 400]

Reports decode tok/s per arm, the median paired ratio, and whether greedy
output matched (MTP should be lossless; oMLX 0.5.7's drafter was not).
"""
import argparse, json, statistics, time, urllib.request
from _key import load_key

BASE = "http://127.0.0.1:8000/v1"
KEY = load_key()
PROMPTS = [
    "Write a Python function that parses an ISO-8601 duration like P3DT4H5M into seconds. Include tests.",
    "Write a React component in TypeScript that renders a sortable table from an array of objects.",
    "Explain how a B-tree insert splits nodes, then give pseudocode.",
]


def gen(model, prompt, max_tokens):
    body = {"model": model, "messages": [{"role": "user", "content": prompt}], "max_tokens": max_tokens,
            "temperature": 0.0, "stream": True, "stream_options": {"include_usage": True},
            "chat_template_kwargs": {"enable_thinking": False}}
    req = urllib.request.Request(f"{BASE}/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"})
    t0, first, text, usage = time.perf_counter(), None, [], None
    with urllib.request.urlopen(req, timeout=1800) as r:
        for raw in r:
            line = raw.decode().strip()
            if not line.startswith("data:") or line == "data: [DONE]":
                continue
            ev = json.loads(line[5:])
            usage = ev.get("usage") or usage
            for ch in ev.get("choices", []):
                d = ch.get("delta", {})
                piece = (d.get("content") or "") + (d.get("reasoning_content") or "")
                if piece and first is None:
                    first = time.perf_counter()
                text.append(piece)
    end = time.perf_counter()
    n = (usage or {}).get("completion_tokens", 0)
    return "".join(text), n / max(end - (first or t0), 1e-3)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("off", help="model id with MTP off")
    ap.add_argument("on", help="model id with MTP on")
    ap.add_argument("--rounds", type=int, default=6)
    ap.add_argument("--max-tokens", type=int, default=400)
    a = ap.parse_args()
    arms = [a.off, a.on]
    for m in arms:
        gen(m, "Say hi.", 8)
    tps = {m: [] for m in arms}
    texts = {m: {} for m in arms}
    ratios = []
    for r in range(a.rounds):
        for i, p in enumerate(PROMPTS):
            order = arms if (r + i) % 2 == 0 else arms[::-1]
            got = {}
            for m in order:
                text, rate = gen(m, p, a.max_tokens)
                got[m] = rate
                tps[m].append(rate)
                texts[m].setdefault(i, set()).add(text)
            ratios.append(got[arms[1]] / got[arms[0]])
            print(f"round {r} prompt {i}: off {got[arms[0]]:.1f}  on {got[arms[1]]:.1f}  x{ratios[-1]:.2f}", flush=True)
    same = sum(texts[arms[0]][i] == texts[arms[1]][i] for i in range(len(PROMPTS)))
    print(json.dumps({
        "off_median_tps": round(statistics.median(tps[arms[0]]), 1),
        "on_median_tps": round(statistics.median(tps[arms[1]]), 1),
        "median_paired_ratio": round(statistics.median(ratios), 3),
        "greedy_identical_prompts": f"{same}/{len(PROMPTS)}",
        "off_deterministic": all(len(s) == 1 for s in texts[arms[0]].values()),
    }, indent=1))


if __name__ == "__main__":
    main()
