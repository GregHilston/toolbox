#!/usr/bin/env bash
# Does this tree install and run for somebody who was not there when it was made?
#
# Three agent runs answered "yes" to their own suite and shipped a package that
# installs for nobody. Each time the agent, the reviewer and the scorer all read
# the same `.venv` that had accumulated during the run, so all three agreed and
# all three were wrong. long-a had deleted `pyarrow` from the dependencies;
# long-b deleted the whole `[build-system]` and hand-made wrapper executables.
#
# So this copies the tree, throws the venv away, resolves from pyproject.toml
# alone, and runs the suite and the entrypoint out of what that produces. It
# needs no container and no agent harness: point it at a directory.
set -uo pipefail

WORKSPACE="${1:-}"
[ -n "${WORKSPACE}" ] || { echo "usage: ${0##*/} <workspace-dir> [build-args...]" >&2; exit 64; }
[ -d "${WORKSPACE}" ]  || { echo "no such directory: ${WORKSPACE}" >&2; exit 66; }
[ -f "${WORKSPACE}/pyproject.toml" ] || { echo "no pyproject.toml in ${WORKSPACE}" >&2; exit 66; }
shift
command -v uv >/dev/null || { echo "uv not found on PATH" >&2; exit 69; }

SCRATCH="$(mktemp -d)"; trap 'rm -rf "${SCRATCH}"' EXIT
log() { printf '==> %s\n' "$*" >&2; }

log "copying ${WORKSPACE} without its venv"
# -a keeps modes; the excludes are the state that makes a dirty tree look green.
( cd "${WORKSPACE}" && tar -cf - \
    --exclude=.venv --exclude=.uv-venv --exclude=.pytest_cache \
    --exclude=__pycache__ --exclude=.ruff_cache --exclude=.git . ) \
  | ( mkdir -p "${SCRATCH}/tree" && cd "${SCRATCH}/tree" && tar -xf - )

cd "${SCRATCH}/tree" || exit 70
export UV_PROJECT_ENVIRONMENT="${SCRATCH}/venv"
# Nothing here may reach the network: a dependency that only resolves because
# this machine happens to be online is still undeclared for the next person.
export UV_OFFLINE="${UV_OFFLINE:-1}"

# A file, not an array: `${#arr[@]}` on an empty array is an unbound variable
# under `set -u` in bash 3.2, which is what /bin/bash still is on macOS.
DEFECTS="${SCRATCH}/defects"; : > "${DEFECTS}"
note() { printf '%s\n' "$1" >> "${DEFECTS}"; }

# Structural, and cheap: a console script is a promise that this installs.
cat > "${SCRATCH}/console_script.py" <<'PYSRC'
import re, sys
try: t = open("pyproject.toml").read()
except OSError: sys.exit(0)
m = re.search(r'^\s*\[project\.(scripts|entry-points\.console_scripts)\]\s*$(.*?)(?=^\s*\[|\Z)',
              t, re.M | re.S)
if not m: sys.exit(0)
e = re.search(r'^\s*["\']?([A-Za-z0-9._-]+)["\']?\s*=', m.group(2), re.M)
print(e.group(1) if e else "")
PYSRC
script_name="$(python3 "${SCRATCH}/console_script.py" 2>/dev/null)"
if [ -n "${script_name}" ] && ! grep -qE '^\s*\[build-system\]' pyproject.toml; then
  note "declares the console script '${script_name}' but has no [build-system], so nothing can install it"
fi

log "resolving from pyproject.toml alone"
if ! sync_out="$(uv sync --quiet 2>&1)"; then
  note "the project does not install from pyproject.toml alone"
  printf '%s\n' "${sync_out}" | tail -8 | sed 's/^/    sync| /' >&2
fi

# The console script must come from the project, not from something on PATH:
# `uv run <name>` falls back to PATH, which is how hand-made wrappers passed.
if [ -n "${script_name}" ] && [ ! -x "${UV_PROJECT_ENVIRONMENT}/bin/${script_name}" ]; then
  note "a clean environment does not contain the console script '${script_name}'"
fi

log "running the suite"
if [ -d tests ]; then
  if pytest_out="$(uv run pytest -q 2>&1)"; then
    printf '%s\n' "${pytest_out}" | tail -1 | sed 's/^/    tests| /' >&2
  else
    note "the suite does not pass from a clean environment"
    printf '%s\n' "${pytest_out}" | tail -8 | sed 's/^/    tests| /' >&2
  fi
else
  note "there are no tests"
fi

if [ -n "${script_name}" ]; then
  log "running ${script_name} $*"
  if build_out="$("${UV_PROJECT_ENVIRONMENT}/bin/${script_name}" "$@" 2>&1)"; then
    printf '%s\n' "${build_out}" | tail -5 | sed 's/^/    run| /' >&2
  else
    note "'${script_name} $*' fails from a clean environment"
    printf '%s\n' "${build_out}" | tail -8 | sed 's/^/    run| /' >&2
  fi
fi

echo
if [ ! -s "${DEFECTS}" ]; then
  echo "OK — ${WORKSPACE} installs and runs from a clean tree"
  exit 0
fi
echo "DEFECTIVE — ${WORKSPACE}"
sed 's/^/  - /' "${DEFECTS}"
exit 1
