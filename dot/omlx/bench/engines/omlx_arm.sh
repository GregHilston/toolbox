#!/bin/bash
# Configure ONE oMLX arm: patch model_settings.json, restart the server clean, wait
# for health.
#
# Per docs/local-llm-benchmarks.md confound #2 (engine-pool residency), every measured
# model gets a freshly restarted server -- a model measured alongside 69GB of other
# resident models read ~30% slow and would have been written up as a real regression.
#
#   ./omlx_arm.sh Qwen3.8-27B-oQ4e-mtp native   # Lightning MTP (fused checkpoint)
#   ./omlx_arm.sh Qwen3.8-27B-oQ4e-mtp none     # no speculation
#   ./omlx_arm.sh Qwen3.8-27B-4bit     vlm      # external drafter (Qwen3.8-27B-MTP-4bit)
#
# WARNING: this WRITES to the stowed dot/omlx/.omlx/model_settings.json, which is the
# real production config. Back it up first and restore when done:
#   cp dot/omlx/.omlx/model_settings.json /tmp/ms.bak
#   ...run the matrix...
#   cp /tmp/ms.bak dot/omlx/.omlx/model_settings.json && git diff --exit-code dot/omlx/
set -euo pipefail
MS="$HOME/Git/toolbox/dot/omlx/.omlx/model_settings.json"
MODEL="$1"
MTP_MODE="$2"   # none | vlm | native

python3 - "$MS" "$MODEL" "$MTP_MODE" <<'PY'
import json, sys
ms_path, model, mode = sys.argv[1], sys.argv[2], sys.argv[3]
d = json.load(open(ms_path))
e = d["models"].setdefault(model, {})
# Sampler parity across every arm and both engines: the official Qwen3.8 contract.
# Requests also send these explicitly; force_sampling is False everywhere, so the
# request wins either way (omlx/server.py:1472) -- this is belt and braces.
e.update({
    "temperature": 1.0, "top_p": 0.95, "top_k": 20, "min_p": 0.0,
    "repetition_penalty": 1.0, "presence_penalty": 0.0,
    # MTPLX has no thinking-budget feature, so oMLX's is disabled for the whole
    # comparison. Leaving it on would cap only oMLX's thinking and nothing else --
    # an asymmetry that shows up as a false wall-clock "win".
    "thinking_budget_enabled": False,
    "chat_template_kwargs": {"reasoning_effort": "medium"},
    "mtp_enabled": mode == "native",
    "vlm_mtp_enabled": mode == "vlm",
})
if mode == "vlm":
    e["vlm_mtp_draft_model"] = "Qwen3.8-27B-MTP-4bit"
else:
    e.pop("vlm_mtp_draft_model", None)
json.dump(d, open(ms_path, "w"), indent=2)
print(f"  model_settings: {model} mode={mode} "
      f"mtp_enabled={e['mtp_enabled']} vlm_mtp_enabled={e['vlm_mtp_enabled']}")
PY

# brew-upgraded oMLX crash-loops if the old process still holds 8000, so kill first.
kill "$(lsof -ti :8000)" 2>/dev/null || true
sleep 3
launchctl kickstart -k "gui/$(id -u)/org.nixos.omlx"
for i in $(seq 1 90); do
  if curl -sf http://127.0.0.1:8000/health >/dev/null 2>&1; then
    echo "  oMLX healthy after ${i}s"; exit 0
  fi
  sleep 1
done
echo "FATAL: oMLX did not come up" >&2; exit 1
