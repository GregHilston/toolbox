#!/bin/bash
# Re-check a finished run from clean, then push the verdict to a phone.
#
# Two problems this solves, both found the hard way on run `long-a`.
#
# The run finished and told nobody: the dataset sat in the instance directory
# and the only way to learn the outcome was to go and look. That does not work
# for a run that ends at 3am, which is the whole point of the exercise.
#
# And "it built" was not true. The agent had deleted `pyarrow` from
# pyproject.toml, so the build passed against the venv that was already on disk
# and fails from a clean checkout — a defect that survived the agent, the
# reviewer, and the scorer, because all three used that same stale venv. So the
# check here deletes `.venv` first. What it reports is whether the artifact
# works for someone who was not there when it was made.
set -uo pipefail
IFS=$'\n\t'

NAME="${1:-}"
[ -n "${NAME}" ] || { echo "usage: ${0##*/} <iteration-name>" >&2; exit 64; }

TOOLBOX="${TOOLBOX:-$HOME/Git/toolbox}"
RUNS="$HOME/Git/agent-runs"
INSTANCE="${RUNS}/iter/${NAME}"
SCRATCH="${RUNS}/clean-${NAME}"
IMAGE="${ARTIFICIUM_IMAGE:-agent-sandbox-hermes:latest}"

[ -d "${INSTANCE}/workspace" ] || { echo "no such run: ${INSTANCE}" >&2; exit 66; }

log() { printf '==> %s\n' "$*" >&2; }

log "re-checking ${NAME} from a clean tree"
rm -rf "${SCRATCH}"; mkdir -p "${SCRATCH}"
cp -R "${INSTANCE}/workspace" "${SCRATCH}/workspace"
rm -rf "${SCRATCH}/workspace/.venv" "${SCRATCH}/workspace/.pytest_cache"

cat > "${SCRATCH}/probe.sh" <<'PROBE'
cd /instance/workspace
printf 'PYTEST=%s\n' "$(timeout 600 uv run pytest -q 2>&1 | tail -1 | tr -d '\r')"
timeout 600 uv run ${BUILD_CMD:-vt-smb build} >/tmp/build.log 2>&1
printf 'BUILD=%s\n' "$?"
tail -2 /tmp/build.log | sed 's/^/BUILDLOG=/'
printf 'ROWS=%s\n' "$(($(wc -l < data/final/businesses.csv 2>/dev/null || echo 1) - 1))"
PROBE

# shellcheck disable=SC2046
out="$(docker run --rm $("${TOOLBOX}/bin/agent-sandbox.sh" --harness hermes _flags "${SCRATCH}" 2>/dev/null) \
  -e AGENT_TASK_MODE=1 -e AGENT_OFFLINE=1 -e UV_OFFLINE=1 \
  -e BUILD_CMD="${AGENT_BUILD_CMD:-vt-smb build}" "${IMAGE}" bash /instance/probe.sh 2>&1)"

pytest_line="$(printf '%s' "${out}" | sed -n 's/^PYTEST=//p' | tail -1)"
build_exit="$(printf '%s' "${out}" | sed -n 's/^BUILD=//p' | tail -1)"
rows="$(printf '%s' "${out}" | sed -n 's/^ROWS=//p' | tail -1)"
buildlog="$(printf '%s' "${out}" | sed -n 's/^BUILDLOG=//p' | tail -1)"

card="$(python3 - "${INSTANCE}/home/kanban.db" <<'PY' 2>/dev/null || echo "?"
import sqlite3, sys
try:
    c = sqlite3.connect(f"file:{sys.argv[1]}?mode=ro", uri=True)
    print(c.execute("select status from tasks order by rowid limit 1").fetchone()[0])
except Exception:
    print("?")
PY
)"
gate="$(grep -c "gate fired" "${INSTANCE}/home/logs/require-green.log" 2>/dev/null || echo 0)"

# The card can be `done` while the artifact does not work for anyone else; that
# gap is the reason this script exists, so say it in the first line.
if [ "${build_exit:-1}" = "0" ] && printf '%s' "${pytest_line}" | grep -q "passed" \
   && ! printf '%s' "${pytest_line}" | grep -q "failed"; then
  verdict="OK"
else
  verdict="DEFECTIVE"
fi

summary="$(printf 'hermes %s: %s (card=%s)\ntests: %s\nclean build: exit %s%s\nrows: %s\ngate fired: %s\n%s' \
  "${NAME}" "${verdict}" "${card}" "${pytest_line:-no result}" "${build_exit:-?}" \
  "$([ "${build_exit:-1}" = "0" ] || printf ' — %s' "${buildlog:0:120}")" \
  "${rows:-0}" "${gate:-0}" "${INSTANCE}/workspace/data/final/businesses.csv")"

printf '\n%s\n\n' "${summary}"

if [ "${AGENT_NOTIFY:-1}" = "1" ]; then
  "${TOOLBOX}/bin/pushover.py" -m "${summary}" >/dev/null 2>&1 \
    && log "pushed" || log "pushover failed (is PUSHOVER_USER_KEY set?)"
fi

rm -rf "${SCRATCH}"
[ "${verdict}" = "OK" ]
