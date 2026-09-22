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
# This name reaches `rm -rf`; `..` would take the whole runs directory with it.
case "${NAME}" in
  *[!a-z0-9-]*|-*|"") echo "bad run name '${NAME}' — lowercase, digits and dashes" >&2; exit 64 ;;
esac

TOOLBOX="${TOOLBOX:-$HOME/Git/toolbox}"
RUNS="$HOME/Git/agent-runs"
INSTANCE="${RUNS}/iter/${NAME}"
# Overridable so a mechanism can be tested with a card small enough to reach a
# handoff. The gate only fires on `kanban_complete`/`kanban_request_review`, so
# proving it works by hoping a hard card finishes is a 50-minute coin flip.
CARD="${AGENT_CARD:-${RUNS}/card.md}"
NOTE="${AGENT_RUN_LOG:-$HOME/Git/notes/ref-hermes-run-log.md}"
STATS="$HOME/.omlx/stats.json"
# agent-verify.sh reads AGENT_BUILD_MODEL; this read MODEL_BUILD and then
# overwrote AGENT_BUILD_MODEL in the container, so the documented override
# silently ran the default and the run-log row named the wrong model.
BUILD="${AGENT_BUILD_MODEL:-${MODEL_BUILD:-Qwen3.6-35B-A3B-4bit-DWQ}}"
JUDGE="${MODEL_JUDGE:-Qwen3.8-27B-4bit}"
CONTAINER=agent-hermes-vt-smb
ROW_ANCHOR='<!-- agent-iterate:rows -->'

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

jget() { printf '%s' "$2" | python3 -c "import json,sys
try: v=json.load(sys.stdin).get('$1')
except Exception: v=None
print('—' if v is None else v)" 2>/dev/null || echo '—'; }

log() { printf '==> %s\n' "$*" >&2; }

rm -rf "${INSTANCE}"; mkdir -p "${INSTANCE}/workspace"
cp "${CARD}" "${INSTANCE}/card.md"
# agent-deliver.sh re-checks the tree in a clean container and must mirror this
# run's network setting; assuming it scored a good tree as a build failure once.
printf '%s' "${AGENT_OFFLINE:-0}" > "${INSTANCE}/offline"
# Pre-seed the source data. Runs 2 and 3 both ignored an explicit "the source is
# known, do not go hunting" and spent their whole budget researching other
# sources instead. Data already on disk removes the temptation entirely and
# isolates "can it build the package" from "will it follow the instruction".
if [ -d "${RUNS}/seed-data" ]; then
  mkdir -p "${INSTANCE}/workspace/data/raw"
  cp "${RUNS}"/seed-data/* "${INSTANCE}/workspace/data/raw/" 2>/dev/null || true
fi

for m in "${BUILD}" "${JUDGE}"; do
  for k in requests prompt_tokens completion_tokens cached_tokens generation_duration prefill_duration; do
    printf -v "b_${m//[.-]/_}_${k}" '%s' "$(stat_of "${STATS}" "$m" "$k")"
  done
done
UV_OFFLINE_FLAG=""
[ "${AGENT_OFFLINE:-0}" = "1" ] && UV_OFFLINE_FLAG=$'-e\nUV_OFFLINE=1'

docker rm -f "${CONTAINER}" >/dev/null 2>&1
start_epoch=$(date +%s)
log "iteration '${NAME}': ${MINUTES}m — ${CHANGE}"
# `_flags` calls die() when a probe target is down, and an empty expansion here
# starts a container with no mounts and no env that exits within seconds.
if ! FLAGS="$("${TOOLBOX}/bin/agent-sandbox.sh" _flags "${INSTANCE}")"; then
  echo "cannot build the sandbox flags — refusing to start a run" >&2
  exit 70
fi
# shellcheck disable=SC2086
docker run -d --name "${CONTAINER}" ${FLAGS} \
  -e AGENT_OFFLINE="${AGENT_OFFLINE:-0}" -e AGENT_BUILD_MODEL="${BUILD}" \
  ${UV_OFFLINE_FLAG} \
  agent-sandbox-hermes:latest >/dev/null 2>&1

alive() { [ "$(docker inspect -f '{{.State.Running}}' "${CONTAINER}" 2>/dev/null)" = "true" ]; }
sleep 5
if ! alive; then
  echo "container exited immediately — see: docker logs ${CONTAINER}" >&2
  docker logs "${CONTAINER}" 2>&1 | tail -20 >&2
  exit 70
fi

end=$(( start_epoch + MINUTES * 60 ))
card_status="?"
# A heartbeat proves the worker is alive, not that it is working. Run `gate-a`
# heartbeated for its whole 51 minutes — the claim lease renews on heartbeat, so
# the dispatcher never reclaimed it — while serving 30 model requests in the
# first ten minutes and then ZERO for twenty. Nothing noticed. Overnight that is
# the difference between losing an hour and losing the night.
#
# Model requests are the progress signal. The builder runs on the DWQ
# checkpoint and nothing else on this box points at it, so its counter is ours;
# a model shared with pi would give false "progress" from the neighbour.
# Counted from oMLX's log, NOT from stats.json. The stats file flushes lazily and
# the lag is unbounded: during run smoke-enriched it sat at 1240 while the log
# showed 11 completions in the previous six minutes, so a stall detector reading
# it would have paged on a healthy run. The log line is timestamped and names the
# model, and the full date is compared so a run crossing midnight still works.
OMLX_LOG="${OMLX_LOG:-$HOME/Library/Logs/omlx.log}"
completions_since() {
  awk -v s="$1" -v m="Chat completion: model=${BUILD}," \
    'index($0, m) { ts = $1 " " substr($2, 1, 8); if (ts >= s) n++ } END { print n+0 }' \
    "${OMLX_LOG}" 2>/dev/null || echo 0
}
run_stamp="$(date '+%F %T')"
STALL_MIN="${AGENT_STALL_MINUTES:-10}"
last_reqs="$(completions_since "${run_stamp}")"
last_progress=$(date +%s)
stall_alerted=0
stalls=0
cards=0
while [ "$(date +%s)" -lt "${end}" ]; do
  sleep 30
  if ! alive; then
    log "container exited after $(( ($(date +%s) - start_epoch) / 60 ))m (card=${card_status})"
    [ "${AGENT_NOTIFY:-1}" = "1" ] && "${TOOLBOX}/bin/agent-notify.sh" \
      -m "hermes ${NAME}: container EXITED $(( ($(date +%s) - start_epoch) / 60 ))m into a ${MINUTES}m run (card=${card_status})" >/dev/null 2>&1 || true
    break
  fi
  board="$(docker exec "${CONTAINER}" hermes kanban list --json 2>/dev/null)"
  card_status="$(printf '%s' "${board}" | python3 -c 'import json,sys
try: print(json.load(sys.stdin)[0]["status"])
except Exception: print("?")' 2>/dev/null || echo "?")"
  # Run 5 was invalidated by scoring one card of a four-card graph as the run.
  cards="$(printf '%s' "${board}" | python3 -c 'import json,sys
try: print(len(json.load(sys.stdin)))
except Exception: print(0)' 2>/dev/null || echo 0)"

  now_reqs="$(completions_since "${run_stamp}")"
  if [ "${now_reqs}" != "${last_reqs}" ]; then
    last_reqs="${now_reqs}"; last_progress=$(date +%s); stall_alerted=0
  elif [ "${stall_alerted}" = "0" ] \
       && [ $(( $(date +%s) - last_progress )) -ge $(( STALL_MIN * 60 )) ]; then
    stall_alerted=1; stalls=$(( stalls + 1 ))
    log "STALL: no model traffic for ${STALL_MIN}m (card=${card_status})"
    # Alert, do not act. Reclaiming a worker that is merely slow would be worse
    # than waiting, and the point here is to stop a wedge going unnoticed.
    if [ "${AGENT_NOTIFY:-1}" = "1" ]; then
      "${TOOLBOX}/bin/agent-notify.sh" -m "hermes ${NAME}: STALLED — no model traffic for ${STALL_MIN}m, $(( ($(date +%s) - start_epoch) / 60 ))m into a ${MINUTES}m run (card=${card_status})" >/dev/null 2>&1 || true
    fi
  fi

  case "${card_status}" in done|blocked) log "card ${card_status} early"; break ;; esac
done
[ "${stalls}" -gt 0 ] && log "${stalls} stall episode(s) during this run"
elapsed=$(( $(date +%s) - start_epoch ))
card_label="${card_status}"
[ "${cards:-0}" -gt 1 ] && card_label="${card_status} (1 of ${cards})"

docker logs "${CONTAINER}" > "${INSTANCE}/container.log" 2>&1
count_gate() {
  docker exec "${CONTAINER}" sh -c \
    "grep -c '$1' /instance/home/logs/require-green.log 2>/dev/null; true" 2>/dev/null \
    | head -1 | tr -cd '0-9'
}
gate_fires="$(count_gate 'gate fired')"; gate_fires="${gate_fires:-0}"
gate_blocks="$(count_gate 'gate blocked')"; gate_blocks="${gate_blocks:-0}"

# Score before stopping the container. pytest and the build command are the
# card's own DONE WHEN criteria, and they only run inside the sandbox, on a
# container that is still up — benching after `docker stop` silently skipped
# both and left every row measuring file counts instead of the objective.
log "scoring (pytest + build inside the sandbox)"
bench="$("${TOOLBOX}/bin/agent-bench.py" "${INSTANCE}/workspace" --harness "${NAME}" \
  --container "${CONTAINER}" --json 2>/dev/null)"
printf '%s' "${bench}" > "${INSTANCE}/score.json"

docker stop "${CONTAINER}" >/dev/null 2>&1

pyfiles=$(jget python_files "${bench}")
loc=$(jget lines_of_code "${bench}")
rows=$(jget dataset_rows "${bench}")
tpass=$(jget tests_passed "${bench}")
tfail=$(jget tests_failed "${bench}")
bexit=$(jget build_exit_code "${bench}")
[ "${rows}" = "—" ] && rows=0

sleep 20   # oMLX flushes stats.json lazily
# Requests and completion tokens alone cannot say where the time went. The
# prompt size and the cache hit rate are what separate "thinking hard" from
# "re-reading the conversation", and they are the two levers worth tuning.
# Python, not awk: macOS ships BWK awk, whose match() takes no array argument,
# so the gawk idiom for pulling the token counts out fails silently here.
deltas="$(python3 "${TOOLBOX}/bin/_omlx_run_traffic.py" "${OMLX_LOG}" "${run_stamp}" "${BUILD}" "${JUDGE}")"

mkdir -p "$(dirname "${NOTE}")"
if ! grep -qF "${ROW_ANCHOR}" "${NOTE}" 2>/dev/null; then
  cat >> "${NOTE}" <<HDR

## Iteration log (appended by \`agent-iterate.sh\`)

| # | Run | Budget | What changed | Card | Files / LOC | Tests p/f | Build | Rows | Gate fired/blocked | Stalls | Model traffic |
|---|---|---|---|---|---|---|---|---|---|---|---|
${ROW_ANCHOR}
HDR
fi

n=$(( $(sed -n "/## Iteration log/,/${ROW_ANCHOR}/p" "${NOTE}" | grep -c '^| [0-9]') + 1 ))
row=$(printf '| %d | `%s` | %dm (ran %dm) | %s | **%s** | %s / %s | %s / %s | %s | %s | %s | %s | %s |' \
  "${n}" "${NAME}" "${MINUTES}" "$(( elapsed / 60 ))" "${CHANGE}" "${card_label}" \
  "${pyfiles}" "${loc}" "${tpass}" "${tfail}" "${bexit}" "${rows}" "${gate_fires:-0}/${gate_blocks:-0}" "${stalls:-0}" "${deltas%<br>}")
python3 - "${NOTE}" "${ROW_ANCHOR}" "${row}" <<'PY'
import sys
path, anchor, row = sys.argv[1:4]
text = open(path).read()
open(path, "w").write(text.replace(anchor, row + "\n" + anchor, 1))
PY

log "recorded row ${n} in ${NOTE}"
printf '\n  card=%s  files=%s  loc=%s  tests=%s pass/%s fail  build_exit=%s  rows=%s  gate=%s fired/blocked  stalls=%s  elapsed=%dm\n' \
  "${card_status}" "${pyfiles}" "${loc}" "${tpass}" "${tfail}" "${bexit}" "${rows}" "${gate_fires:-0}/${gate_blocks:-0}" "${stalls:-0}" "$(( elapsed / 60 ))"
printf '  score: %s\n\n' "${INSTANCE}/score.json"

# The in-run score is measured against the venv the agent built up over the run.
# `long-a` passed that and still shipped a tree that does not build for anyone
# else. Re-check from clean and push the verdict, so a run that ends unattended
# reports itself.
"${TOOLBOX}/bin/agent-deliver.sh" "${NAME}" || true
