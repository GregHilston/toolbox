#!/bin/bash
# Refuse `kanban_complete` unless the suite and the entrypoint actually pass.
#
# Run 1 shipped a package whose CLI crashed on import and four tests that had
# drifted from the code, and the review gate approved it anyway. The reviewer's
# SOUL told it to run what it approves; it did not. An instruction to a small
# model is not a gate. This is.
#
# Wired as a pre_tool_call hook, which is the one hook class Hermes lets veto a
# call: exit 2, or {"decision":"block"} on stdout, and the call does not happen.
# The failure output becomes the reason the agent sees, so it gets concrete
# evidence rather than a refusal.
set -uo pipefail

WORKSPACE="${GATE_WORKSPACE:-/instance/workspace}"
# --help, not build: it exercises import and CLI wiring — the exact failure that
# shipped last run (ImportError on a mis-cased class name) — without a network
# fetch that would make every completion attempt cost minutes.
BUILD_CMD="${GATE_BUILD_CMD:-uv run vt-smb --help}"
LOG="${GATE_LOG:-/instance/home/logs/require-green.log}"
mkdir -p "$(dirname "${LOG}")" 2>/dev/null || LOG=/dev/null

payload="$(cat)"
tool="$(printf '%s' "${payload}" | python3 -c 'import json,sys
try: print((json.load(sys.stdin) or {}).get("tool_name",""))
except Exception: print("")' 2>/dev/null)"

# Only gate the one call that means "this work is finished".
case "${tool}" in
  kanban_complete) ;;
  *) exit 0 ;;
esac

block() {
  printf '%s\n' "$1" | head -c 2500 | python3 -c 'import json,sys
print(json.dumps({"decision":"block","reason":sys.stdin.read()}))'
  exit 0
}

{ printf '[%s] gate fired for %s\n' "$(date -u +%FT%TZ)" "${tool}"; } >> "${LOG}" 2>/dev/null

cd "${WORKSPACE}" 2>/dev/null || exit 0        # nothing built yet; nothing to gate
[ -f pyproject.toml ] || exit 0

if ! out="$(timeout 200 uv run pytest -q 2>&1)"; then
  block "kanban_complete refused: the test suite does not pass. Fix this before completing.

$(printf '%s' "${out}" | tail -40)"
fi

if ! out="$(timeout 60 bash -lc "${BUILD_CMD}" 2>&1)"; then
  block "kanban_complete refused: the suite passes but '${BUILD_CMD}' fails, so the entrypoint does not even import. Tests passing while the CLI cannot import is exactly the gap that shipped last run.

$(printf '%s' "${out}" | tail -40)"
fi

{ printf '[%s] gate passed\n' "$(date -u +%FT%TZ)"; } >> "${LOG}" 2>/dev/null
exit 0
