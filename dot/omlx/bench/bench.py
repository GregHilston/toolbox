#!/usr/bin/env python3
"""
oMLX decode-throughput A/B harness.

Replicates the methodology of dot/omlx/speculative-decoding-findings.md:
  matched A/B, same server instance, temperature 0, identical prompts,
  prompt families = code / prose / qa, ~500 prompt tokens -> 200 completion tokens.

Uses streaming so prefill (TTFT) and decode are measured separately:
  decode_tps = (n_tokens - 1) / (t_last - t_first)
which is the number bandwidth-bound analysis actually predicts.
"""
import json, sys, time, urllib.request, statistics, argparse, os

BASE = "http://127.0.0.1:8000/v1"
KEY = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "omlx_key")).read().strip()

# ---- prompt families (~500 prompt tokens each), mirroring the findings doc ----
CODE = """You are reviewing a Python module. Here is the file:

```python
import asyncio, logging
from dataclasses import dataclass, field
from typing import Optional, Callable, Awaitable

log = logging.getLogger(__name__)

@dataclass
class RetryPolicy:
    attempts: int = 3
    base_delay: float = 0.25
    max_delay: float = 8.0
    jitter: bool = True
    retry_on: tuple = (TimeoutError, ConnectionError)

@dataclass
class Circuit:
    failure_threshold: int = 5
    reset_timeout: float = 30.0
    _failures: int = field(default=0, init=False)
    _opened_at: Optional[float] = field(default=None, init=False)

    def allow(self) -> bool:
        if self._opened_at is None:
            return True
        if (time.monotonic() - self._opened_at) > self.reset_timeout:
            self._opened_at = None
            self._failures = 0
            return True
        return False

    def record_failure(self):
        self._failures += 1
        if self._failures >= self.failure_threshold:
            self._opened_at = time.monotonic()

    def record_success(self):
        self._failures = 0
        self._opened_at = None

async def call_with_retry(fn: Callable[[], Awaitable], policy: RetryPolicy, circuit: Circuit):
    last = None
    for i in range(policy.attempts):
        if not circuit.allow():
            raise RuntimeError("circuit open")
        try:
            out = await fn()
            circuit.record_success()
            return out
        except policy.retry_on as e:
            last = e
            circuit.record_failure()
            delay = min(policy.base_delay * (2 ** i), policy.max_delay)
            await asyncio.sleep(delay)
    raise last
```

Write a corrected version of this module. Fix every bug you find and explain each fix briefly."""

PROSE = """Write a clear, well-structured technical essay of several paragraphs on the following topic.

Topic: The trade-offs of running large language models locally on consumer hardware versus
calling a hosted API. Cover at minimum: capital cost versus marginal cost, data privacy and
regulatory considerations, latency characteristics (time-to-first-token versus sustained
throughput), the operational burden of model lifecycle management, how quantization changes
the calculus, the role of unified memory architectures, and the situations in which a local
model is strictly better, strictly worse, or genuinely a matter of taste. Be concrete and
avoid marketing language. Assume the reader is an experienced software engineer who has not
yet run a model locally but is technically fluent and skeptical of hype. Do not use bullet
points; write flowing prose. Begin immediately with the essay itself, with no preamble."""

QA = """Answer the following question thoroughly and precisely.

Question: A colleague claims that speculative decoding will roughly double inference speed for
any transformer model, on any hardware, as long as the drafter is small and fast. Explain
carefully under what conditions this claim holds and under what conditions it fails. In your
answer, address: what resource speculative decoding actually trades against what; why the
arithmetic intensity of the decode step matters; how a mixture-of-experts model with a small
number of active parameters per token differs from a dense model of the same total parameter
count; why draft acceptance rate alone is not sufficient to predict speedup; and how a unified
memory architecture with high bandwidth changes the picture relative to a discrete GPU with
limited VRAM. Give a concrete rule of thumb an engineer could apply before investing effort."""

PROMPTS = {"code": CODE, "prose": PROSE, "qa": QA}


def stream_once(model, prompt, max_tokens=200, temperature=0.0, extra=None, timeout=1200):
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": True,
        "stream_options": {"include_usage": True},
    }
    if extra:
        body.update(extra)
    req = urllib.request.Request(
        f"{BASE}/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"},
    )
    t0 = time.perf_counter()
    t_first = None
    t_last = None
    n = 0
    usage = None
    text = []
    with urllib.request.urlopen(req, timeout=timeout) as r:
        for raw in r:
            line = raw.decode("utf-8").strip()
            if not line.startswith("data:"):
                continue
            payload = line[5:].strip()
            if payload == "[DONE]":
                break
            try:
                ev = json.loads(payload)
            except json.JSONDecodeError:
                continue
            if ev.get("usage"):
                usage = ev["usage"]
            for ch in ev.get("choices", []):
                d = ch.get("delta", {}) or {}
                piece = d.get("content") or d.get("reasoning_content") or ""
                if piece:
                    now = time.perf_counter()
                    if t_first is None:
                        t_first = now
                    t_last = now
                    n += 1
                    text.append(piece)
    t_end = time.perf_counter()
    if t_first is None:
        return None
    wall = t_end - t0
    ttft = t_first - t0
    comp = (usage or {}).get("completion_tokens", n)
    # oMLX batches several tokens into one SSE chunk, so chunk counts are NOT token
    # counts. Derive decode rate from usage.completion_tokens and the post-prefill span.
    decode_span = (wall - ttft) or 1e-9
    return {
        "ttft": ttft,
        "wall": wall,
        "chunks": n,
        "completion_tokens": comp,
        "prompt_tokens": (usage or {}).get("prompt_tokens"),
        "prefill_tps": ((usage or {}).get("prompt_tokens") or 0) / ttft if ttft > 0 else 0.0,
        # decode-only rate: excludes prefill
        "decode_tps": comp / decode_span,
        # end-to-end rate including prefill == the findings doc's
        # "completion tokens / wall time"
        "e2e_tps": comp / wall,
        "text": "".join(text),
    }


def bench_model(model, reps=3, max_tokens=200, extra=None, families=None):
    families = families or list(PROMPTS)
    print(f"\n{'='*72}\nMODEL: {model}  (extra={extra})\n{'='*72}", flush=True)
    # warm-up: forces load + kernel warm, discarded
    w0 = time.perf_counter()
    stream_once(model, "Hi.", max_tokens=8, extra=extra)
    print(f"  [warm-up / load: {time.perf_counter()-w0:.1f}s]", flush=True)

    out = {}
    for fam in families:
        runs = []
        for i in range(reps):
            r = stream_once(model, PROMPTS[fam], max_tokens=max_tokens, extra=extra)
            if r:
                runs.append(r)
                print(
                    f"  {fam:6s} run{i+1}: decode {r['decode_tps']:6.2f} t/s | "
                    f"e2e {r['e2e_tps']:6.2f} t/s | ttft {r['ttft']:5.2f}s "
                    f"(prefill {r['prefill_tps']:6.0f} t/s) | "
                    f"in {r['prompt_tokens']} / out {r['completion_tokens']} tok",
                    flush=True,
                )
        if runs:
            out[fam] = {
                "decode_tps": statistics.median(x["decode_tps"] for x in runs),
                "e2e_tps": statistics.median(x["e2e_tps"] for x in runs),
                "ttft": statistics.median(x["ttft"] for x in runs),
                "prefill_tps": statistics.median(x["prefill_tps"] for x in runs),
                "completion_tokens": runs[0]["completion_tokens"],
                "prompt_tokens": runs[0]["prompt_tokens"],
                "runs": [{k: v for k, v in x.items() if k != "text"} for x in runs],
            }
    if out:
        print(
            f"  --> MEDIAN decode: "
            + "  ".join(f"{k}={v['decode_tps']:.2f}" for k, v in out.items())
            + f"   AVG={statistics.mean(v['decode_tps'] for v in out.values()):.2f} t/s",
            flush=True,
        )
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("models", nargs="+")
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--max-tokens", type=int, default=200)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    results = {}
    for m in args.models:
        try:
            results[m] = bench_model(m, reps=args.reps, max_tokens=args.max_tokens)
        except Exception as e:
            print(f"  !! {m} failed: {type(e).__name__}: {e}", flush=True)
            results[m] = {"error": f"{type(e).__name__}: {e}"}

    if args.out:
        slim = {
            m: {f: {k: v for k, v in d.items() if k != "runs"} for f, d in r.items()}
            if "error" not in r else r
            for m, r in results.items()
        }
        with open(args.out, "w") as fh:
            json.dump(slim, fh, indent=2)
        print(f"\nwrote {args.out}", flush=True)
