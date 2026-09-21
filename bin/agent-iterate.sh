#!/bin/bash
# One scored Hermes iteration: fresh instance, one card, fixed budget, then
# append a row to the run log in the vault.
#
# The point is a tight loop. Long runs answer "how good is the output"; these
# answer "did the change help", and they have to be cheap enough to run many
# times. Everything lands in the note so the record survives this session.
set -uo pipefail
IFS=$'\n\t'

NAME="${1:-}"; MINUTES="${2:-15}"; CHANGE="${3:-}"
[ -n "${NAME}" ] || { echo "usage: ${0##*/} <name> <minutes> '<what changed>'" >&2; exit 64; }

TOOLBOX="${TOOLBOX:-$HOME/Git/toolbox}"
RUNS="$HOME/Git/agent-runs"
INSTANCE="${RUNS}/iter/${NAME}"
CARD="${RUNS}/card.md"
NOTE="${AGENT_RUN_LOG:-$HOME/Git/notes/ref-hermes-run-log.md}"
STATS="$HOME/.omlx/stats.json"
BUILD="${MODEL_BUILD:-Qwen3.6-35B-A3B-4bit-DWQ}"
JUDGE="${MODEL_JUDGE:-Qwen3.8-27B-4bit}"
CONTAINER=agent-hermes-vt-smb

stat_of() {
  python3 - "$1" "$2" "$3" <<'PY'
import json, sys
try:
    d = json.load(open(sys.argv[1]))
    print((d.get("per_model") or {}).get(sys.argv[2], {}).get(sys.argv[3], 0))
except Exception:
    print(0)
PY
}

log() { printf '==> %s\n' "$*" >&2; }

rm -rf "${INSTANCE}"; mkdir -p "${INSTANCE}/workspace"
cp "${CARD}" "${INSTANCE}/card.md"

for m in "${BUILD}" "${JUDGE}"; do
  for k in requests prompt_tokens completion_tokens generation_duration prefill_duration; do
    printf -v "b_${m//[.-]/_}_${k}" '%s' "$(stat_of "${STATS}" "$m" "$k")"
  done
done

docker rm -f "${CONTAINER}" >/dev/null 2>&1
start_epoch=$(date +%s)
log "iteration '${NAME}': ${MINUTES}m — ${CHANGE}"
# shellcheck disable=SC2046
docker run -d --name "${CONTAINER}" $("${TOOLBOX}/bin/agent-sandbox.sh" _flags "${INSTANCE}" 2>/dev/null) \
  agent-sandbox-hermes:latest >/dev/null 2>&1

end=$(( start_epoch + MINUTES * 60 ))
card_status="?"
while [ "$(date +%s)" -lt "${end}" ]; do
  sleep 30
  card_status="$(docker exec "${CONTAINER}" hermes kanban list --json 2>/dev/null \
    | python3 -c 'import json,sys
try: print(json.load(sys.stdin)[0]["status"])
except Exception: print("?")' 2>/dev/null || echo "?")"
  case "${card_status}" in done|blocked) log "card ${card_status} early"; break ;; esac
done
elapsed=$(( $(date +%s) - start_epoch ))

docker logs "${CONTAINER}" > "${INSTANCE}/container.log" 2>&1
gate_blocks=$(docker exec "${CONTAINER}" sh -c 'grep -c "gate fired" /instance/home/logs/require-green.log 2>/dev/null' 2>/dev/null || echo 0)
docker stop "${CONTAINER}" >/dev/null 2>&1

sleep 20   # oMLX flushes stats.json lazily
bench="$("${TOOLBOX}/bin/agent-bench.py" "${INSTANCE}/workspace" --harness "${NAME}" --json 2>/dev/null)"
pyfiles=$(printf '%s' "${bench}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["python_files"])' 2>/dev/null || echo 0)
loc=$(printf '%s' "${bench}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["lines_of_code"])' 2>/dev/null || echo 0)
rows=$(printf '%s' "${bench}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["dataset_rows"] or 0)' 2>/dev/null || echo 0)
tests=$(cd "${INSTANCE}/workspace" 2>/dev/null && ls tests >/dev/null 2>&1 && echo yes || echo no)

deltas=""
for m in "${BUILD}" "${JUDGE}"; do
  v="${m//[.-]/_}"
  r=$(( $(stat_of "${STATS}" "$m" requests) - $(eval echo "\$b_${v}_requests") ))
  ct=$(( $(stat_of "${STATS}" "$m" completion_tokens) - $(eval echo "\$b_${v}_completion_tokens") ))
  deltas="${deltas}${m}: ${r} reqs / ${ct} completion tokens<br>"
done

mkdir -p "$(dirname "${NOTE}")"
[ -f "${NOTE}" ] || cat > "${NOTE}" <<'HDR'
---
tags: [llm, ai, agents, hermes, experiment]
related:
  - "[[ref-hermes-kanban-improvements]]"
  - "[[ref-artificium-vs-hermes-kanban]]"
---

Short scored Hermes iterations on moria. One card, fixed budget, same rubric
every time, so a change can be attributed. Long-run results live in
[[ref-hermes-kanban-improvements]].

**The card** is fixed across runs (`~/Git/agent-runs/card.md`): build a minimal
`vt_smb` package against a known Socrata endpoint and emit a scored dataset.
`DONE WHEN` requires pytest green, `vt-smb build` exit 0, >=100 rows, and every
row carrying `outreach_score` and `outreach_reason`.

| # | Run | Budget | What changed | Card | Files / LOC | Rows | Gate blocks | Model traffic | Verdict |
|---|---|---|---|---|---|---|---|---|---|
HDR

n=$(grep -c '^| [0-9]' "${NOTE}" 2>/dev/null || echo 0); n=$(( n + 1 ))
printf '| %d | `%s` | %dm (ran %dm) | %s | **%s** | %s / %s | %s | %s | %s | |\n' \
  "${n}" "${NAME}" "${MINUTES}" "$(( elapsed / 60 ))" "${CHANGE}" "${card_status}" \
  "${pyfiles}" "${loc}" "${rows}" "${gate_blocks:-0}" "${deltas%<br>}" >> "${NOTE}"

log "recorded row ${n} in ${NOTE}"
printf '\n  card=%s  files=%s  loc=%s  rows=%s  gate_blocks=%s  elapsed=%dm\n\n' \
  "${card_status}" "${pyfiles}" "${loc}" "${rows}" "${gate_blocks:-0}" "$(( elapsed / 60 ))"
