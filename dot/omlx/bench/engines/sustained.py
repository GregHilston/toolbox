#!/usr/bin/env python3
"""
Sustained decode -- one realistic coding task generated to thousands of tokens.

THIS IS THE ARM THAT MATTERS, and the reason it exists: burst decode over 200 tokens
said MTPLX and oMLX were within 4% of each other, while this said MTPLX was 1.5x
faster. The gap is oMLX's MTP depth controller parking mid-request (see
docs/mtplx-vs-omlx.md SS4). A 200-token benchmark is too short to ever see it.

Always run >=4 reps. Parking is intermittent -- it hit 2 of 4 runs -- so two reps can
easily report either 31 t/s or 18 t/s as "the" number.

  ./sustained.py --arm omlx_mtp --model Qwen3.8-27B-oQ4e-mtp --reps 4 --out sus.json
  grep 'MTP\\[' ~/Library/Logs/omlx.log    # finish=length = good, finish=parked = bailed
"""
import argparse
import json
import statistics
import time

import _engine

TASK = """Implement a complete, single-file Python module `ratelimit.py` providing a
token-bucket rate limiter suitable for an async HTTP client.

Requirements:
- `class TokenBucket` with `capacity: float`, `refill_rate: float` (tokens/sec), monotonic clock.
- `async def acquire(self, tokens: float = 1.0, timeout: float | None = None) -> bool`
  which waits until enough tokens are available, returning False on timeout without consuming.
- Fair FIFO ordering: waiters are served in arrival order, no barging.
- `class MultiBucket` keying independent buckets by string, with an LRU eviction bound.
- A decorator `@rate_limited(bucket, tokens=1.0)` that works on async functions.
- Correct behaviour under cancellation: a cancelled waiter must not leak its reservation.
- Full type hints, docstrings, and a `if __name__ == "__main__":` self-test that
  demonstrates burst, sustained rate, fairness, and timeout.

Write the complete file. Explain your concurrency design before the code."""

ap = argparse.ArgumentParser()
ap.add_argument("--arm", required=True)
ap.add_argument("--base", default="http://127.0.0.1:8000/v1")
ap.add_argument("--key", default=None)
ap.add_argument("--model", required=True)
ap.add_argument("--max-tokens", type=int, default=6000)
ap.add_argument("--reps", type=int, default=4)
ap.add_argument("--temperature", type=float, default=_engine.QWEN38_TEMPERATURE)
ap.add_argument("--extra", default=json.dumps(_engine.QWEN38_EXTRA))
ap.add_argument("--out", required=True)
a = ap.parse_args()

bench = _engine.bind(a.base, a.key or _engine.load_omlx_key() or "placeholder")
extra = json.loads(a.extra) if a.extra else {}

print(f"### SUSTAINED {a.arm}: {a.base} model={a.model} cap={a.max_tokens}", flush=True)
t0 = time.perf_counter()
bench.stream_once(a.model, "Hi.", max_tokens=8, temperature=a.temperature, extra=extra)
print(f"  [warm-up/load {time.perf_counter() - t0:.1f}s]", flush=True)

runs = []
for i in range(a.reps):
    r = bench.stream_once(a.model, TASK, max_tokens=a.max_tokens,
                          temperature=a.temperature, extra=extra, timeout=3600)
    txt = r.pop("text")
    r["chars"] = len(txt)
    r["has_code_fence"] = "```" in txt
    r["tail"] = txt[-400:]
    runs.append(r)
    print(f"  run{i+1}: decode {r['decode_tps']:7.2f} t/s | wall {r['wall']:7.1f}s | "
          f"ttft {r['ttft']:5.2f}s | out {r['completion_tokens']} tok | "
          f"{r['chars']} chars | fence={r['has_code_fence']}", flush=True)

out = {"arm": a.arm, "base": a.base, "model": a.model, "max_tokens": a.max_tokens,
       "extra": extra, "temperature": a.temperature,
       "median_decode_tps": statistics.median(x["decode_tps"] for x in runs),
       "min_decode_tps": min(x["decode_tps"] for x in runs),
       "max_decode_tps": max(x["decode_tps"] for x in runs),
       "median_wall": statistics.median(x["wall"] for x in runs),
       "median_out_tokens": statistics.median(x["completion_tokens"] for x in runs),
       "runs": runs}
print(f"  ==> {a.arm}: median {out['median_decode_tps']:.2f} t/s "
      f"(spread {out['min_decode_tps']:.1f}-{out['max_decode_tps']:.1f}) over "
      f"{out['median_out_tokens']:.0f} tokens", flush=True)
if out["max_decode_tps"] > 1.4 * out["min_decode_tps"]:
    print("  !! >1.4x spread across reps -- on oMLX check for finish=parked in the log",
          flush=True)

with open(a.out, "w") as fh:
    json.dump(out, fh, indent=2)
print(f"wrote {a.out}", flush=True)
