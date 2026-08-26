#!/usr/bin/env python3
"""
Does turning speculation on change the output at all? Engine-agnostic.

Speculative decoding with greedy verification is supposed to be bit-identical to plain
decoding -- that is the entire appeal: free speed, no quality question. MTPLX's card
claims "speculation in MTPLX is exact"; oMLX makes the same implicit claim.

ALWAYS capture the off-vs-off control across a server restart too. Without it a
divergence is uninterpretable -- you cannot tell a real effect from ordinary
nondeterminism. Measured 2026-08-24: control 3/3 identical on both engines, spec-on
2/3 on both. See docs/mtplx-vs-omlx.md SS4.

  ./lossless.py capture omlx_off  --model Qwen3.8-27B-oQ4e-mtp    # mtp_enabled false
  ./lossless.py capture omlx_off2 --model Qwen3.8-27B-oQ4e-mtp    # again, after restart
  ./lossless.py capture omlx_on   --model Qwen3.8-27B-oQ4e-mtp    # mtp_enabled true
  ./lossless.py compare omlx_off omlx_off2     # <- the control; expect 3/3
  ./lossless.py compare omlx_off omlx_on       # <- the test
"""
import argparse
import hashlib
import json
import os
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
import _engine  # noqa: E402

PROMPTS = [
    "Write a Python function to merge overlapping intervals. Explain the algorithm.",
    "List the first 12 primes and explain the sieve of Eratosthenes.",
    "Explain the difference between a process and a thread.",
]

ap = argparse.ArgumentParser()
ap.add_argument("mode", choices=["capture", "compare"])
ap.add_argument("a")
ap.add_argument("b", nargs="?")
ap.add_argument("--base", default="http://127.0.0.1:8000/v1")
ap.add_argument("--key", default=None)
ap.add_argument("--model", default=None)
ap.add_argument("--max-tokens", type=int, default=180)
a = ap.parse_args()

BASE = a.base.rstrip("/")
KEY = a.key or _engine.load_omlx_key() or "placeholder"


def gen(prompt):
    body = {"model": a.model, "messages": [{"role": "user", "content": prompt}],
            "max_tokens": a.max_tokens,
            "temperature": 0.0,  # greedy => deterministic => comparable
            "reasoning_effort": "medium",
            "chat_template_kwargs": {"reasoning_effort": "medium"}}
    req = urllib.request.Request(
        f"{BASE}/chat/completions", data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=1800) as r:
        d = json.load(r)
    m = d["choices"][0]["message"]
    return (m.get("reasoning_content") or "") + "\x00" + (m.get("content") or "")


def path(label):
    return os.path.join(HERE, f"lossless_{label}.json")


if a.mode == "compare":
    x = json.load(open(path(a.a)))
    y = json.load(open(path(a.b)))
    same = sum(p["sha"] == q["sha"] for p, q in zip(x, y))
    for i, (p, q) in enumerate(zip(x, y)):
        verdict = "IDENTICAL" if p["sha"] == q["sha"] else "DIFFERS"
        print(f"  prompt {i}: {verdict:9s} ({p['sha'][:12]} vs {q['sha'][:12]})  "
              f"len {p['chars']} vs {q['chars']}")
    print(f"  => {same}/{len(x)} identical "
          f"({'LOSSLESS' if same == len(x) else 'NOT lossless'})")
else:
    if not a.model:
        raise SystemExit("--model is required for capture")
    out = []
    for p in PROMPTS:
        t = gen(p)
        out.append({"prompt": p[:50], "sha": hashlib.sha256(t.encode()).hexdigest(),
                    "chars": len(t)})
        print(f"  {out[-1]['sha'][:12]}  {out[-1]['chars']:6d} chars  {p[:44]}")
    with open(path(a.a), "w") as fh:
        json.dump(out, fh, indent=2)
    print(f"wrote {path(a.a)}")
