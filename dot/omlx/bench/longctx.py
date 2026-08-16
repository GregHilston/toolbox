#!/usr/bin/env python3
"""
Long-context prefill cost.

For a coding agent the felt latency is usually PREFILL, not decode: you paste a
40k-token repo context and wait for the first token. Decode t/s says nothing about
that. This measures TTFT vs prompt length.

Qwen3.8/3.6-27B are hybrid: only 16 of 64 layers carry a real KV cache
(full_attention_interval 4), so long context should be cheaper than a conventional
dense 27B. This checks whether that shows up in practice.

MEASUREMENT HAZARD -- the reason this script looks the way it does. oMLX runs a
prefix cache (32 GB hot cache on moria). An earlier version built each prompt as
`header + CHUNK*reps + question` and walked the sizes in ascending order, so every
prompt was a strict prefix-extension of the previous one and got most of its prefill
served from cache. The tell was unmistakable in the output: a 7,862-token prompt
came back FASTER in wall-clock than a 1,946-token one. Those numbers measured the
cache, not prefill.

Two defences here:
  1. Every prompt gets a unique random nonce in its FIRST line, so no prompt is a
     prefix of any other and nothing can be served from a previous request.
  2. Sizes are visited in shuffled order, and a warm-up request absorbs model load,
     so any residual ordering effect cannot masquerade as a size trend.
"""
import json, os, sys, time, urllib.request

BASE = "http://127.0.0.1:8000/v1"
HERE = os.path.dirname(os.path.abspath(__file__))
from _key import load_key

KEY = load_key()
MODEL = sys.argv[1] if len(sys.argv) > 1 else "Qwen3.8-27B-4bit"

# A chunk of plausible source-like text; repeated to hit target lengths.
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
    body = {"model": MODEL, "messages": [{"role": "user", "content": prompt}],
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


if __name__ == "__main__":
    import random, secrets
    print(f"model={MODEL}   (thinking disabled; output capped so wall ~= prefill)")
    print("unique nonce per prompt + shuffled order => no prefix-cache reuse\n")

    # warm-up: absorb model load so it cannot be charged to the first size
    once(build(500, secrets.token_hex(8)))  # returns 4-tuple; discarded

    targets = [2000, 8000, 16000, 32000, 64000]
    random.shuffle(targets)
    rows = []
    for target in targets:
        try:
            pt, ct, wall, cached = once(build(target, secrets.token_hex(8)))
            tps = pt / wall if wall else 0
            rows.append({"prompt_tokens": pt, "completion_tokens": ct,
                         "wall": round(wall, 2), "prefill_tps": round(tps, 1),
                         "cached_tokens": cached})
            # cached_tokens MUST be ~0; anything else means we measured the cache
            flag = "" if cached == 0 else f"  <-- WARNING {cached} CACHED, not a cold prefill"
            print(f"  {pt:7d} prompt tok -> {wall:7.2f}s   ({tps:7.0f} tok/s prefill), "
                  f"out {ct}, cached {cached}{flag}", flush=True)
        except Exception as e:
            print(f"  target {target}: FAILED {type(e).__name__}: {e}", flush=True)
            break
    rows.sort(key=lambda r: r["prompt_tokens"])
    safe = MODEL.replace("/", "_")
    json.dump(rows, open(os.path.join(HERE, f"longctx_{safe}.json"), "w"), indent=2)
