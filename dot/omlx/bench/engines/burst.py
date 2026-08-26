#!/usr/bin/env python3
"""
Burst decode throughput for one engine arm -- 200 tokens, 3 reps, code/prose/qa.

Same prompts, same math, same reps as `../bench.py`; the only difference is that the
endpoint is a flag, so oMLX and MTPLX are measured by identical code.

  ./burst.py --arm mtplx_mtp --base http://127.0.0.1:18080/v1 --key benchkey \
             --model mtplx-qwen38-27b-optimized-speed --out arm_mtplx_mtp.json
"""
import argparse
import json
import statistics
import time

import _engine

ap = argparse.ArgumentParser()
ap.add_argument("--arm", required=True, help="label for this configuration")
ap.add_argument("--base", default="http://127.0.0.1:8000/v1")
ap.add_argument("--key", default=None, help="default: the oMLX key")
ap.add_argument("--model", required=True)
ap.add_argument("--reps", type=int, default=3)
ap.add_argument("--max-tokens", type=int, default=200)
ap.add_argument("--temperature", type=float, default=_engine.QWEN38_TEMPERATURE)
ap.add_argument("--extra", default=json.dumps(_engine.QWEN38_EXTRA))
ap.add_argument("--out", required=True)
a = ap.parse_args()

bench = _engine.bind(a.base, a.key or _engine.load_omlx_key() or "placeholder")
extra = json.loads(a.extra) if a.extra else {}

print(f"### ARM {a.arm}: {a.base} model={a.model} temp={a.temperature} extra={extra}",
      flush=True)

# Warm-up absorbs model load and kernel warm; discarded so it cannot be charged to
# the first prompt family.
t0 = time.perf_counter()
bench.stream_once(a.model, "Hi.", max_tokens=8, temperature=a.temperature, extra=extra)
print(f"  [warm-up/load {time.perf_counter() - t0:.1f}s]", flush=True)

res = {"arm": a.arm, "base": a.base, "model": a.model, "temperature": a.temperature,
       "extra": extra, "started": time.strftime("%Y-%m-%dT%H:%M:%S"), "families": {}}

for fam in ("code", "prose", "qa"):
    runs = []
    for i in range(a.reps):
        r = bench.stream_once(a.model, bench.PROMPTS[fam], max_tokens=a.max_tokens,
                              temperature=a.temperature, extra=extra)
        runs.append(r)
        print(f"  {fam:6s} run{i+1}: decode {r['decode_tps']:7.2f} t/s | "
              f"e2e {r['e2e_tps']:7.2f} | ttft {r['ttft']:5.2f}s "
              f"(prefill {r['prefill_tps']:6.0f} t/s) | "
              f"in {r['prompt_tokens']} / out {r['completion_tokens']}", flush=True)
    res["families"][fam] = {
        "decode_tps": statistics.median(x["decode_tps"] for x in runs),
        "e2e_tps": statistics.median(x["e2e_tps"] for x in runs),
        "ttft": statistics.median(x["ttft"] for x in runs),
        "prefill_tps": statistics.median(x["prefill_tps"] for x in runs),
        "prompt_tokens": runs[0]["prompt_tokens"],
        "runs": [{k: v for k, v in x.items() if k != "text"} for x in runs],
    }

res["mean_decode_tps"] = statistics.mean(v["decode_tps"] for v in res["families"].values())
res["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S")
print(f"  ==> ARM {a.arm} MEAN DECODE {res['mean_decode_tps']:.2f} t/s  "
      + "  ".join(f"{k}={v['decode_tps']:.1f}" for k, v in res["families"].items()),
      flush=True)

with open(a.out, "w") as fh:
    json.dump(res, fh, indent=2)
print(f"wrote {a.out}", flush=True)
