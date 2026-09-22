#!/bin/bash
# Qwen3.6-35B-A3B-4bit vs its 4-bit-DWQ sibling, on the axis the original
# comparison never measured.
#
# The existing verdict rests on decode throughput (130.7 vs 103.6 tok/s) and a
# 10-task coding eval that ceilings out at 10/10 vs 9/10. Neither settles the
# question for an agent run, because an agent's time does not go where a decode
# benchmark looks: on a real Hermes run the builder carried a 31k-token prompt at
# 86% cache hit and generated ~2k tokens a turn. The long-context prefill table
# in docs/local-llm-benchmarks.md has a DWQ-shaped hole in it, and prefill is
# where the two checkpoints differ structurally — DWQ runs the whole attention
# stack at 8-bit where the plain build runs it at 4.
#
# Both models, one pass, then the first re-measured last so session drift cannot
# be mistaken for a difference. Absolute numbers on a live desktop move ~20%
# between sessions; only ratios measured inside one pass are trustworthy.
set -uo pipefail
IFS=$'\n\t'

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT="${1:-${HERE}/showdown-$(date +%Y%m%d-%H%M%S)}"
PLAIN=Qwen3.6-35B-A3B-4bit
DWQ=Qwen3.6-35B-A3B-4bit-DWQ

mkdir -p "${OUT}"
log() { printf '\n==> %s\n' "$*" | tee -a "${OUT}/run.log"; }

# A benchmark that shares the GPU measures the neighbour. Refuse rather than
# quietly produce a number nobody can act on.
if docker ps --format '{{.Names}}' | grep -q '^agent-hermes'; then
  echo "FATAL: an agent run is live; it would contend for the GPU" >&2
  exit 1
fi

# Restart before EVERY measured model, not once at the top. oMLX keeps every
# model it has served resident, so a single restart leaves the second arm
# measured alongside the first arm's 19 GB — which is the benchmark README's
# rule #1, and ignoring it cost this comparison a whole pass: the drift control
# came back 22% slower than the identical first pass and the run had to be
# thrown away.
restart_omlx() {
  log "restarting oMLX so this model is measured alone"
  launchctl kickstart -k "gui/$(id -u)/org.nixos.omlx" 2>&1 | tee -a "${OUT}/run.log"
  until curl -s -o /dev/null -m 3 http://127.0.0.1:8000/v1/models; do sleep 3; done
  # Settle: a kickstart returns before the server is done reclaiming the old
  # process's memory, and a measurement started into that reads slow.
  sleep 20
}

# One window per model, because contention_audit.sh takes a single expected id
# and would otherwise report the other arm of this very benchmark as foreign.
measure() {
  local model="$1" tag="$2"
  local window="${OUT}/window-${tag}.txt"
  restart_omlx
  # One second of margin so the previous arm's last request cannot land inside
  # this window and be reported as foreign, which it was on the first attempt.
  sleep 1
  printf 'START %s\n' "$(date '+%F %T')" > "${window}"

  log "decode throughput: ${model} (${tag})"
  python3 "${HERE}/bench.py" "${model}" --reps 3 --out "${OUT}/decode_${tag}.json" \
    2>&1 | tee -a "${OUT}/run.log"

  log "prefill vs prompt length: ${model} (${tag})"
  python3 "${HERE}/longctx.py" "${model}" 2>&1 | tee -a "${OUT}/run.log"
  cp "${HERE}/longctx_${model}.json" "${OUT}/longctx_${tag}.json" 2>/dev/null

  printf 'END %s\n' "$(date '+%F %T')" >> "${window}"
  log "auditing ${tag}'s window for anything else that touched the GPU"
  "${HERE}/contention_audit.sh" "${window}" "${model}" 2>&1 | tee -a "${OUT}/run.log"
}

measure "${PLAIN}" "plain"
measure "${DWQ}" "dwq"
# The drift control: if the plain model disagrees with its own first pass, the
# session moved under us and the comparison is worth less than it looks.
measure "${PLAIN}" "plain-repeat"

log "results in ${OUT}"
