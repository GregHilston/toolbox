#!/usr/bin/env python3
"""
Capture greedy output from a model and hash it.

Speculative decoding with greedy verification is lossless BY CONSTRUCTION -- the
target accepts only the prefix it would itself have produced. This turns that claim
into evidence: run with the drafter off, run with it on, compare hashes.

Usage:
    lossless_check.py <model> <label>     # writes lossless_<label>.json
    lossless_check.py --compare a b       # compares two captures
"""
import hashlib, json, os, sys, urllib.request

BASE = "http://127.0.0.1:8000/v1"
HERE = os.path.dirname(os.path.abspath(__file__))
KEY = open(os.path.join(HERE, "omlx_key")).read().strip()

PROMPTS = [
    "Write a Python function to merge overlapping intervals. Explain the algorithm.",
    "List the first 12 primes and explain the sieve of Eratosthenes.",
    "Explain the difference between a process and a thread.",
]


def gen(model, prompt, max_tokens=180):
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.0,          # greedy => deterministic => comparable
    }
    req = urllib.request.Request(
        f"{BASE}/chat/completions", data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=1800) as r:
        d = json.load(r)
    m = d["choices"][0]["message"]
    return (m.get("reasoning_content") or "") + "\x00" + (m.get("content") or "")


if __name__ == "__main__":
    if sys.argv[1] == "--compare":
        a = json.load(open(os.path.join(HERE, f"lossless_{sys.argv[2]}.json")))
        b = json.load(open(os.path.join(HERE, f"lossless_{sys.argv[3]}.json")))
        same = 0
        for i, (x, y) in enumerate(zip(a, b)):
            ok = x["sha"] == y["sha"]
            same += ok
            print(f"  prompt {i}: {'IDENTICAL' if ok else 'DIFFERS'}  ({x['sha'][:12]} vs {y['sha'][:12]})")
        print(f"  => {same}/{len(a)} identical "
              f"({'LOSSLESS' if same == len(a) else 'NOT lossless - investigate'})")
    else:
        model, label = sys.argv[1], sys.argv[2]
        out = []
        for p in PROMPTS:
            t = gen(model, p)
            out.append({"sha": hashlib.sha256(t.encode()).hexdigest(), "chars": len(t)})
            print(f"  captured {out[-1]['sha'][:12]} ({out[-1]['chars']} ch)", flush=True)
        json.dump(out, open(os.path.join(HERE, f"lossless_{label}.json"), "w"), indent=2)
