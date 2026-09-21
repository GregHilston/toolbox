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
  kanban_complete|kanban_request_review) ;;
  *) exit 0 ;;
esac

block() {
  # Log the refusal as well as the firing. Counting only "gate fired" cannot
  # distinguish a gate that waved everything through from one that caught
  # something, and that difference is the only reason the gate exists.
  { printf '[%s] gate blocked %s: %s\n' "$(date -u +%FT%TZ)" "${tool}" \
      "$(printf '%s' "$1" | head -1)"; } >> "${LOG}" 2>/dev/null
  printf '%s\n' "$1" | head -c 2500 | python3 -c 'import json,sys
print(json.dumps({"decision":"block","reason":sys.stdin.read()}))'
  exit 0
}

{ printf '[%s] gate fired for %s\n' "$(date -u +%FT%TZ)" "${tool}"; } >> "${LOG}" 2>/dev/null

cd "${WORKSPACE}" 2>/dev/null || exit 0        # nothing built yet; nothing to gate
[ -f pyproject.toml ] || exit 0

if ! out="$(timeout 200 uv run pytest -q 2>&1)"; then
  block "${tool} refused: the test suite does not pass. Fix this before handing the work on.

$(printf '%s' "${out}" | tail -40)"
fi

if ! out="$(timeout 60 bash -lc "${BUILD_CMD}" 2>&1)"; then
  block "${tool} refused: the suite passes but '${BUILD_CMD}' fails, so the entrypoint does not even import. Tests passing while the CLI cannot import is exactly the gap that shipped last run.

$(printf '%s' "${out}" | tail -40)"
fi

# Everything above this line runs against the venv that accumulated during the
# run, which is why both runs that ever completed a card shipped a tree that
# installs for nobody. long-a dropped pyarrow from the dependencies; long-b
# deleted the whole [build-system] and every dependency and hand-made wrapper
# executables in .venv. Green, both times, and uninstallable, both times.
#
# Conditioned on [project.scripts]: a library with no console script is a
# legitimate virtual project and uv will not install it either way. Declaring
# an entrypoint is the promise that this installs, and long-b kept the promise
# while deleting everything that could keep it.
if grep -q '^\[project\.scripts\]' pyproject.toml; then
  missing=""
  grep -q '^\[build-system\]' pyproject.toml || missing="a [build-system] table"
  grep -q '^dependencies' pyproject.toml \
    || missing="${missing:+${missing} and }a dependencies list"
  if [ -n "${missing}" ]; then
    block "${tool} refused: pyproject.toml declares a console script under [project.scripts] but is missing ${missing}, so nothing can install it. The suite and the entrypoint only pass here because .venv already holds what they need; a clean checkout gets nothing. Restore the packaging rather than working around it — deleting the build system is not a fix for a build error."
  fi
fi

# The structural check above cannot see a dependency that was dropped while the
# list itself survived, so resolve the project into a throwaway environment and
# run the entrypoint out of that. UV_OFFLINE keeps it to the image cache, so
# this costs seconds and only happens on a handoff.
GATE_VENV="${GATE_VENV:-/tmp/gate-clean-venv}"
rm -rf "${GATE_VENV}"
if ! out="$(UV_PROJECT_ENVIRONMENT="${GATE_VENV}" timeout 180 bash -lc "${BUILD_CMD}" 2>&1)"; then
  rm -rf "${GATE_VENV}"
  block "${tool} refused: '${BUILD_CMD}' works against the .venv in the workspace and fails in a clean environment built from pyproject.toml alone. Whatever it needs is installed but not declared, so nobody else can build this.

$(printf '%s' "${out}" | tail -40)"
fi
rm -rf "${GATE_VENV}"

{ printf '[%s] gate passed\n' "$(date -u +%FT%TZ)"; } >> "${LOG}" 2>/dev/null
exit 0
