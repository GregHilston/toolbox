#!/usr/bin/env python3
"""results/*/summary.json -> one markdown table row per arm."""
import glob, json, os, statistics

HERE = os.path.dirname(os.path.abspath(__file__))
print("| arm | model | first try | final | hints | out tokens | wall | decode tok/s | swap peak |")
print("|---|---|---|---|---|---|---|---|---|")
for p in sorted(glob.glob(os.path.join(HERE, "results", "*", "summary.json"))):
    s = json.load(open(p))
    r = s["rounds"]
    last = r[-1]
    print(f"| {s['arm']} | {s['model']} | {r[0]['score']}/{r[0]['of']} | {last['score']}/{last['of']} "
          f"| {len(r) - 1} | {sum(x['completion_tokens'] for x in r):,} | {sum(x['wall_s'] for x in r) / 60:.1f} min "
          f"| {statistics.median(x['decode_tps'] for x in r):.1f} | {max(x['swap_peak_mb'] for x in r):.0f} MB |")
