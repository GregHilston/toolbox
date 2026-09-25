#!/usr/bin/env bash
# Race the two builder models on the same Kanban card, then score them.
#
#   hermes-builder-ab.sh enqueue [repeats]   # default 3 per model
#   hermes-builder-ab.sh score <run-dir>
#
# Repeats matter: two byte-identical runs once produced 16 files and 0 files,
# so one run per model measures noise (notes: ref-hermes-run-log.md).
# The board runs one card at a time, so enqueueing all of them is safe.
set -euo pipefail

TOOLBOX="${HOME}/Git/toolbox"
SEED="${TOOLBOX}/hermes/seed"
RAW="${HOME}/Git/agent-runs/workspace/data/raw/vt-childcare-providers.json"
MODELS=(Qwen3.6-35B-A3B-4bit-DWQ Qwen3.8-27B-4bit)

short() { case "$1" in Qwen3.6*) echo moe ;; Qwen3.8*) echo dense ;; esac; }

enqueue() {
  local repeats="${1:-3}"
  local run="${HOME}/Git/agent-runs/builder-ab/$(date +%Y%m%d-%H%M)"
  mkdir -p "${run}"
  # Alternating models spreads any drift over the night across both arms.
  for i in $(seq 1 "${repeats}"); do
    for model in "${MODELS[@]}"; do
      local name dir id
      name="$(short "${model}")-${i}"
      dir="${run}/${name}"
      mkdir -p "${dir}/data/raw"
      cp "${SEED}/project/pyproject.toml" "${SEED}/project/ENGINEERING.md" "${dir}/"
      cp "${RAW}" "${dir}/data/raw/"
      git -C "${dir}" init -q
      git -C "${dir}" add -A
      git -C "${dir}" commit -qm seed
      id="$(hermes kanban create "builder-ab ${name}" \
        --assignee builder \
        --workspace "dir:${dir}" \
        --model "${model}" \
        --goal --goal-max-turns 8 \
        --max-runtime 4h \
        --body-file "${SEED}/cards/builder-ab.md" \
        --idempotency-key "builder-ab-${run##*/}-${name}" \
        --json | jq -r '.id')"
      echo "${model}" > "${dir}/.ab-model"
      echo "${id}" > "${dir}/.ab-task"
      echo "${name}  ${id}  ${dir}"
    done
  done
  echo
  echo "Watch:  caffeinate -dims hermes kanban tail"
  echo "Score:  ${0##*/} score ${run}"
}

# The expected output comes from the raw file, not from any run.
expected() {
  jq -r '
    group_by(.county)
    | map({c: .[0].county, n: length,
           cap: (map(.total_licensed_capacity | tonumber) | add)})
    | sort_by(-.cap, .c)
    | "county,providers,capacity", (.[] | "\(.c),\(.n),\(.cap)")' "${RAW}"
}

score() {
  local run="${1:?usage: score <run-dir>}"
  local want; want="$(expected)"
  printf '%-8s %-9s %8s %5s %-7s %-6s\n' run status minutes runs clean output
  for dir in "${run}"/*/; do
    dir="${dir%/}"
    [ -f "${dir}/.ab-task" ] || continue
    local id row status minutes runs clean output
    id="$(cat "${dir}/.ab-task")"
    row="$(sqlite3 -separator ' ' "${HOME}/.hermes/kanban.db" \
      "SELECT status,
              COALESCE((completed_at - started_at) / 60, '-'),
              (SELECT COUNT(*) FROM task_runs WHERE task_id = t.id)
       FROM tasks t WHERE id = '${id}'")"
    read -r status minutes runs <<< "${row}"
    if installs-from-clean.sh "${dir}" childcare-capacity >/dev/null 2>&1; then clean=pass; else clean=FAIL; fi
    if [ "$(cd "${dir}" && uv run --quiet vt-smb childcare-capacity 2>/dev/null)" = "${want}" ]; then
      output=match
    else
      output=WRONG
    fi
    printf '%-8s %-9s %8s %5s %-7s %-6s\n' "${dir##*/}" "${status}" "${minutes}" "${runs}" "${clean}" "${output}"
  done
}

case "${1:-}" in
  enqueue) shift; enqueue "$@" ;;
  score)   shift; score "$@" ;;
  expected) expected ;;
  *) sed -n '2,9p' "$0" >&2; exit 64 ;;
esac
