#!/usr/bin/env python3
"""
Long-context prefill cost.

For a coding agent the felt latency is usually PREFILL, not decode: you paste a
40k-token repo context and wait for the first token. Decode t/s says nothing about
that. This measures TTFT vs prompt length.

Qwen3.8/3.6-27B are hybrid: only 16 of 64 layers carry a real KV cache
(full_attention_interval 4), so long context should be cheaper than a conventional
dense 27B. This checks whether that shows up in practice.
"""
import json, os, sys, time, urllib.request

BASE = "http://127.0.0.1:8000/v1"
HERE = os.path.dirname(os.path.abspath(__file__))
KEY = open(os.path.join(HERE, "omlx_key")).read().strip()
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


def build(target_tokens):
    # ~4 chars/token is close enough for MLX tokenizers on code-like text
    reps = max(1, (target_tokens * 4) // len(CHUNK))
    return ("Here is a source file:\n\n" + CHUNK * reps +
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
    return u.get("prompt_tokens"), u.get("completion_tokens"), wall


if __name__ == "__main__":
    print(f"model={MODEL}   (thinking disabled; output capped so wall ~= prefill)\n")
    rows = []
    for target in (2000, 8000, 16000, 32000, 64000):
        try:
            pt, ct, wall = once(build(target))
            tps = pt / wall if wall else 0
            rows.append({"prompt_tokens": pt, "completion_tokens": ct,
                         "wall": round(wall, 2), "prefill_tps": round(tps, 1)})
            print(f"  {pt:7d} prompt tok -> {wall:7.2f}s   ({tps:7.0f} tok/s prefill), out {ct}",
                  flush=True)
        except Exception as e:
            print(f"  target {target}: FAILED {type(e).__name__}: {e}", flush=True)
            break
    json.dump(rows, open(os.path.join(HERE, f"longctx_{MODEL}.json"), "w"), indent=2)
