#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""A/B/A/B decode comparison, because measuring the arms one after another failed twice.

Two sequential attempts at ranking `Qwen3.6-35B-A3B-4bit` against its 4-bit-DWQ
sibling were both thrown out by their own drift control:

  attempt 1  one oMLX restart at the top, so the second arm carried the first
             arm's 19 GB. Control came back 22% slow.
  attempt 2  a restart before every arm, which fixed residency and left thermal
             drift: plain measured 130.92 t/s at the start of the pass and
             110.12 at the end. A 16% session drift cannot rank a ~18% effect.

The fix is not a better control, it is a design where drift cancels. Both models
are warmed first so residency is identical and stable, then the two are sampled
alternately. Each round yields a PAIRED ratio taken seconds apart; a machine that
slides under both arms slides under both halves of every pair. The reported
figure is the median of the paired ratios, and the spread of those ratios — not a
difference of two averages taken minutes apart — is what says whether the answer
is real.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _key import load_key  # noqa: E402

BASE = "http://127.0.0.1:8000/v1"
PLAIN = "Qwen3.6-35B-A3B-4bit"
DWQ = "Qwen3.6-35B-A3B-4bit-DWQ"

# Code-shaped and long enough that decode, not per-request overhead, dominates.
PROMPT = (
    "Write a Python function `merge_intervals(intervals)` that merges overlapping "
    "closed integer intervals and returns them sorted. Handle the empty list, "
    "single intervals, intervals that touch at an endpoint, and fully nested "
    "intervals. Include a docstring and brief inline reasoning about the sort key."
)


def once(model: str, key: str, max_tokens: int = 200) -> dict:
    body = {
        "model": model,
        "messages": [{"role": "user", "content": PROMPT}],
        "max_tokens": max_tokens,
        "temperature": 0.0,
        "stream": True,
        "stream_options": {"include_usage": True},
        "chat_template_kwargs": {"enable_thinking": False},
    }
    req = urllib.request.Request(
        f"{BASE}/chat/completions", data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    t0 = time.perf_counter()
    ttft = None
    usage = {}
    with urllib.request.urlopen(req, timeout=1800) as resp:
        for raw in resp:
            line = raw.decode().strip()
            if not line.startswith("data: "):
                continue
            payload = line[6:]
            if payload == "[DONE]":
                break
            chunk = json.loads(payload)
            if chunk.get("usage"):
                usage = chunk["usage"]
            choices = chunk.get("choices") or []
            if ttft is None and choices and (choices[0].get("delta") or {}).get("content"):
                ttft = time.perf_counter() - t0
    wall = time.perf_counter() - t0
    completion = usage.get("completion_tokens") or 0
    # Decode rate excludes time to first token, so prefill is not folded in.
    decode_span = wall - (ttft if ttft is not None else 0.0)
    return {
        "decode_tps": completion / decode_span if decode_span > 0 else 0.0,
        "completion_tokens": completion,
        "ttft": ttft,
        "wall": wall,
    }


CHUNK = """
def process_batch(records, *, validate=True, on_error="skip"):
    \"\"\"Normalize a batch of records and return (ok, failed).\"\"\"
    ok, failed = [], []
    for i, rec in enumerate(records):
        try:
            if validate and not isinstance(rec, dict):
                raise TypeError(f"record {i} is {type(rec).__name__}, expected dict")
            out = {k.strip().lower(): v for k, v in rec.items() if v is not None}
            if "id" not in out:
                raise KeyError(f"record {i} missing id")
            ok.append(out)
        except Exception as exc:
            if on_error == "raise":
                raise
            failed.append((i, repr(exc)))
    return ok, failed
"""


def long_prompt(target_tokens: int, nonce: str) -> str:
    """The nonce goes FIRST so no prompt is a prefix of any other.

    oMLX runs a 32 GB prefix cache. Without this the second arm of a pair reads
    its neighbour's cache instead of its own prefill, and a bigger prompt comes
    back faster than a smaller one.
    """
    reps = max(1, (target_tokens * 4) // len(CHUNK))
    return (f"Session {nonce}. Here is a source file:\n\n" + CHUNK * reps +
            "\n\nName the single most likely bug in process_batch. One sentence.")


def prefill_once(model: str, key: str, target_tokens: int) -> dict:
    import secrets
    body = {
        "model": model,
        "messages": [{"role": "user", "content": long_prompt(target_tokens, secrets.token_hex(8))}],
        "max_tokens": 24, "temperature": 0.0,
        "chat_template_kwargs": {"enable_thinking": False},
    }
    req = urllib.request.Request(
        f"{BASE}/chat/completions", data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=3600) as r:
        d = json.load(r)
    wall = time.perf_counter() - t0
    u = d.get("usage", {})
    cached = (u.get("prompt_tokens_details") or {}).get("cached_tokens", 0)
    pt = u.get("prompt_tokens") or 0
    return {"prefill_tps": pt / wall if wall else 0.0, "prompt_tokens": pt,
            "cached": cached, "wall": wall}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--rounds", type=int, default=6)
    ap.add_argument("--prefill-tokens", type=int, default=0,
                    help="measure prefill at this prompt size instead of decode")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    key = load_key()

    print("warming both models so residency is identical and stable", flush=True)
    for m in (PLAIN, DWQ):
        r = once(m, key, max_tokens=16)
        print(f"  {m}: loaded ({r['wall']:.1f}s)", flush=True)

    rows = []
    print(f"\n{'round':>5}  {'plain':>9}  {'DWQ':>9}  {'DWQ/plain':>10}", flush=True)
    for i in range(1, args.rounds + 1):
        # Order flips each round so a systematic within-pair position effect
        # (the second call of a pair running on a marginally hotter chip) cannot
        # accumulate in one arm's favour.
        order = (PLAIN, DWQ) if i % 2 else (DWQ, PLAIN)
        if args.prefill_tokens:
            samples = {m: prefill_once(m, key, args.prefill_tokens) for m in order}
            for m, s in samples.items():
                if s["cached"]:
                    print(f"  !! {m} served {s['cached']} cached tokens — not a cold prefill",
                          file=sys.stderr)
            got = {m: s["prefill_tps"] for m, s in samples.items()}
        else:
            got = {m: once(m, key)["decode_tps"] for m in order}
        ratio = got[DWQ] / got[PLAIN] if got[PLAIN] else 0.0
        rows.append({"round": i, "first": order[0], "plain": got[PLAIN],
                     "dwq": got[DWQ], "ratio": ratio})
        print(f"{i:5d}  {got[PLAIN]:9.2f}  {got[DWQ]:9.2f}  {ratio:10.3f}", flush=True)

    ratios = [r["ratio"] for r in rows]
    med = statistics.median(ratios)
    print(f"\n  paired ratio: median {med:.3f}  "
          f"(min {min(ratios):.3f}, max {max(ratios):.3f})")
    axis = f"prefill@{args.prefill_tokens}" if args.prefill_tokens else "decode"
    print(f"  DWQ {axis} cost: {(med - 1) * 100:+.1f}%")
    drift = (rows[-1]["plain"] - rows[0]["plain"]) / rows[0]["plain"] * 100
    print(f"  plain drifted {drift:+.1f}% across the pass — pairing is what absorbs this")
    if args.out:
        json.dump({"rows": rows, "median_ratio": med}, open(args.out, "w"), indent=2)
        print(f"\n  wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
