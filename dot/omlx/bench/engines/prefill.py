#!/usr/bin/env python3
"""
Prefill cost vs prompt length, for any OpenAI-compatible engine.

Port of ../longctx.py with the endpoint as a flag. It keeps that script's two
defences, and they are NOT optional -- see docs/local-llm-benchmarks.md trap #3, where
a 4x longer prompt returned FASTER in wall-clock because every prompt was a strict
prefix-extension of the last and was served from the prefix cache:

  1. a unique random nonce in the FIRST line of every prompt, so no prompt is a prefix
     of any other;
  2. shuffled size order plus a warm-up, so residual ordering effects cannot look like
     a size trend.

`cached_tokens` is asserted 0 on every row where the server reports it. MTPLX does not
report the field; there the nonce is the whole defence, which is why it is per-prompt
random rather than per-run.

  ./prefill.py --model Qwen3.8-27B-oQ4e-mtp --label omlx_mtp
"""
import argparse
import json
import os
import random
import secrets
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
import _engine  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--model", required=True)
ap.add_argument("--base", default="http://127.0.0.1:8000/v1")
ap.add_argument("--key", default=None)
ap.add_argument("--label", default=None, help="output filename stem")
ap.add_argument("--targets", default="2000,8000,16000,32000,64000")
ap.add_argument("--out-dir", default=HERE)
a = ap.parse_args()

BASE = a.base.rstrip("/")
KEY = a.key or _engine.load_omlx_key() or "placeholder"

CHUNK = '''
def process_batch(records, *, validate=True, on_error="skip"):
    """Normalize a batch of records and return (ok, failed)."""
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
'''


def build(target_tokens, nonce):
    # ~4 chars/token is close enough for MLX tokenizers on code-like text.
    # The nonce goes FIRST so this prompt shares no prefix with any other.
    reps = max(1, (target_tokens * 4) // len(CHUNK))
    return (f"Session {nonce}. Here is a source file:\n\n" + CHUNK * reps +
            "\n\nName the single most likely bug in process_batch. One sentence.")


def once(prompt, max_tokens=24):
    body = {"model": a.model, "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens, "temperature": 0.0,
            "chat_template_kwargs": {"enable_thinking": False}}
    req = urllib.request.Request(
        f"{BASE}/chat/completions", data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"})
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=3600) as r:
        d = json.load(r)
    wall = time.perf_counter() - t0
    u = d.get("usage", {})
    cached = (u.get("prompt_tokens_details") or {}).get("cached_tokens", 0)
    return u.get("prompt_tokens"), u.get("completion_tokens"), wall, cached


print(f"model={a.model} base={BASE}  (thinking off; output capped so wall ~= prefill)")
print("unique nonce per prompt + shuffled order => no prefix-cache reuse\n")

once(build(500, secrets.token_hex(8)))  # warm-up, discarded

targets = [int(x) for x in a.targets.split(",")]
random.shuffle(targets)
rows = []
for target in targets:
    try:
        pt, ct, wall, cached = once(build(target, secrets.token_hex(8)))
        tps = pt / wall if wall else 0
        rows.append({"prompt_tokens": pt, "completion_tokens": ct,
                     "wall": round(wall, 2), "prefill_tps": round(tps, 1),
                     "cached_tokens": cached})
        flag = "" if not cached else f"  <-- WARNING {cached} CACHED, not a cold prefill"
        print(f"  {pt:7d} prompt tok -> {wall:7.2f}s   ({tps:7.0f} tok/s prefill), "
              f"out {ct}, cached {cached}{flag}", flush=True)
    except Exception as e:
        print(f"  target {target}: FAILED {type(e).__name__}: {e}", flush=True)
        break

rows.sort(key=lambda r: r["prompt_tokens"])
stem = (a.label or a.model).replace("/", "_")
path = os.path.join(a.out_dir, f"prefill_{stem}.json")
with open(path, "w") as fh:
    json.dump(rows, fh, indent=2)
print(f"wrote {path}")
