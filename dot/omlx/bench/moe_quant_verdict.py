#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Turn the showdown's raw numbers into the one figure the choice turns on.

Decode tok/s ranks these two checkpoints one way and prefill tok/s can rank them
another, and neither is what an agent run spends its night doing. An agent turn
is a partly-cached prompt followed by a long generation, so the honest figure is
seconds per turn at the mix a real run actually produced — measured, not assumed:
pass `--avg-prompt`, `--cached-frac` and `--completion` from a real run's oMLX log.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def prefill_tps(rows: list[dict], uncached_tokens: float) -> float:
    """Interpolate the measured prefill curve at the run's real prompt size.

    Rate is not flat across length — it rose to ~1,480 tok/s at 16K and fell to
    ~830 at 64K on this box — so taking any single row stands in for the wrong
    prompt.
    """
    pts = sorted((r["prompt_tokens"], r["prefill_tps"]) for r in rows if r.get("prefill_tps"))
    if not pts:
        raise SystemExit("no prefill rows")
    if uncached_tokens <= pts[0][0]:
        return pts[0][1]
    if uncached_tokens >= pts[-1][0]:
        return pts[-1][1]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if x0 <= uncached_tokens <= x1:
            t = (uncached_tokens - x0) / (x1 - x0)
            return y0 + t * (y1 - y0)
    return pts[-1][1]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("results", help="a showdown output directory")
    ap.add_argument("--avg-prompt", type=float, default=31400)
    ap.add_argument("--cached-frac", type=float, default=0.86)
    ap.add_argument("--completion", type=float, default=2075)
    args = ap.parse_args()

    out = Path(args.results)
    decode = {}
    for tag in ("plain", "dwq"):
        decode.update(json.loads((out / f"decode_{tag}.json").read_text()))
    uncached = args.avg_prompt * (1 - args.cached_frac)

    print(f"\nagent turn = {uncached:,.0f} uncached prompt tokens + "
          f"{args.completion:,.0f} completion tokens")
    print(f"(from a real run: {args.avg_prompt:,.0f} avg prompt, "
          f"{args.cached_frac:.0%} cached)\n")

    table = {}
    for model, tag in (("Qwen3.6-35B-A3B-4bit", "plain"),
                       ("Qwen3.6-35B-A3B-4bit-DWQ", "dwq")):
        rows = json.loads((out / f"longctx_{tag}.json").read_text())
        p_tps = prefill_tps(rows, uncached)
        d_tps = decode_tps(decode, model)
        t_prefill, t_decode = uncached / p_tps, args.completion / d_tps
        table[model] = (p_tps, d_tps, t_prefill, t_decode, t_prefill + t_decode)
        print(f"  {model}")
        print(f"    prefill {p_tps:8.0f} tok/s -> {t_prefill:6.1f}s")
        print(f"    decode  {d_tps:8.1f} tok/s -> {t_decode:6.1f}s")
        print(f"    turn                        {t_prefill + t_decode:6.1f}s\n")

    a, b = table["Qwen3.6-35B-A3B-4bit"], table["Qwen3.6-35B-A3B-4bit-DWQ"]
    ratio = b[4] / a[4]
    print(f"  DWQ costs {ratio:.2f}x per turn "
          f"({(ratio - 1) * 100:+.0f}%) -> {1 / ratio:.2f}x the turns in a fixed night")
    print(f"  over 8 hours: {8 * 3600 / a[4]:.0f} turns vs {8 * 3600 / b[4]:.0f}\n")
    return 0


def decode_tps(decode: dict, model: str) -> float:
    """bench.py writes {model: {family: {"decode_tps": ...}}}.

    The `code` family, not the mean over all three: this ranks a checkpoint for a
    coding agent, and prose and qa are a different token distribution.
    """
    families = decode.get(model)
    if not isinstance(families, dict) or "error" in families:
        raise SystemExit(f"no decode result for {model}: {families}")
    if "code" in families:
        return float(families["code"]["decode_tps"])
    rates = [float(f["decode_tps"]) for f in families.values() if "decode_tps" in f]
    if not rates:
        raise SystemExit(f"no decode_tps for {model}")
    return sum(rates) / len(rates)


if __name__ == "__main__":
    raise SystemExit(main())
