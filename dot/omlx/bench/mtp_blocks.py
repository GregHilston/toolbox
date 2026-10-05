#!/usr/bin/env python3
"""
Lightning MTP on vs off for a model too big to hold twice in memory.

mtp_paired.py alternates every request between an MTP-on id and its MTP-off
twin, so oMLX holds both. A model over half of RAM cannot: each switch evicts
the other and reloads it. This runs blocks instead, off/on/on/off/off/on, with
oMLX restarted before each so only one copy is resident.

    mtp_blocks.py <mtp-off-id> <mtp-on-id>

Same prompts, greedy identity check and report as mtp_paired.py.
"""
import json, os, statistics, subprocess, sys, time, urllib.request
from mtp_paired import gen, PROMPTS, KEY

OFF, ON = sys.argv[1], sys.argv[2]
ORDER = [OFF, ON, ON, OFF, OFF, ON]


def restart():
    subprocess.run(["launchctl", "kickstart", "-k", f"gui/{os.getuid()}/org.nixos.omlx"], check=True)
    for _ in range(120):
        try:
            urllib.request.urlopen(urllib.request.Request(
                "http://127.0.0.1:8000/v1/models", headers={"Authorization": f"Bearer {KEY}"}), timeout=5)
            return
        except Exception:
            time.sleep(2)
    raise SystemExit("oMLX did not come back")


tps = {OFF: [], ON: []}
texts = {OFF: {}, ON: {}}
for b, m in enumerate(ORDER):
    restart()
    gen(m, "Say hi.", 8)
    for i, p in enumerate(PROMPTS):
        text, rate = gen(m, p, 400)
        tps[m].append(rate)
        texts[m].setdefault(i, set()).add(text)
        print(f"block {b} {'on ' if m == ON else 'off'} prompt {i}: {rate:.1f} tok/s", flush=True)
same = sum(texts[OFF][i] == texts[ON][i] for i in range(len(PROMPTS)))
print(json.dumps({
    "off_median_tps": round(statistics.median(tps[OFF]), 1),
    "on_median_tps": round(statistics.median(tps[ON]), 1),
    "ratio_of_medians": round(statistics.median(tps[ON]) / statistics.median(tps[OFF]), 3),
    "greedy_identical_prompts": f"{same}/{len(PROMPTS)}",
    "off_deterministic": all(len(s) == 1 for s in texts[OFF].values()),
    "on_deterministic": all(len(s) == 1 for s in texts[ON].values()),
}, indent=1))
