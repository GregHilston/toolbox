#!/bin/bash
# Build, seed and drive a sandboxed long-running agent. Two harnesses share one
# sandbox so the comparison between them is about the harness, not the cage.
# See agent-sandbox/CLAUDE.md.
set -euo pipefail
IFS=$'\n\t'

# Hermes only. Artificium was removed after the head-to-head: its text
# `<tool_call>` protocol collides with oMLX's unconditional tool-call extraction
# and it landed zero tool calls in 80 requests. See
# ~/Git/notes/ref-artificium-vs-hermes-kanban.md. `--harness hermes` is still
# accepted so older commands and docs keep working.
if [ "${1:-}" = "--harness" ]; then
  [ "${2:-}" = "hermes" ] || { echo "only the hermes harness remains" >&2; exit 64; }
  shift 2
fi
HARNESS=hermes

RUNS_DIR="${AGENT_RUNS_DIR:-$HOME/Git/agent-runs}"
SANDBOX_DIR="${AGENT_SANDBOX_DIR:-$HOME/Git/toolbox/agent-sandbox}"
REFERENCE="${RUNS_DIR}/reference"

IMAGE="agent-sandbox-${HARNESS}:latest"
CONTAINER="agent-${HARNESS}-vt-smb"
INSTANCE="${RUNS_DIR}/vt-smb/${HARNESS}"

MODEL="${AGENT_MODEL:-Qwen3.6-35B-A3B-4bit-DWQ}"
CONTEXT_WINDOW="${AGENT_CONTEXT_WINDOW:-131072}"
WORKING_MEMORY="${AGENT_WORKING_MEMORY:-96000}"

# Exported, not passed on the command line: `--env=NAME` reads it from this
# process, so the key never shows up in `ps` on the host.
export ARTIFICIUM_API_KEY="${ARTIFICIUM_API_KEY:-${OMLX_API_KEY:-}}"
export OMLX_API_KEY="${OMLX_API_KEY:-}"

BLOCKED_PROBES=""

# Repositories exported read-only as background reference.
REFERENCE_REPOS=(
  "toolbox:${HOME}/Git/toolbox"
  "home-lab:${HOME}/Git/home-lab"
  "notes:${HOME}/Git/notes"
)

die() { printf '%s: %s\n' "${0##*/}" "$*" >&2; exit 1; }
log() { printf '==> %s\n' "$*" >&2; }

require_docker() {
  command -v docker >/dev/null 2>&1 || die "docker not found"
  docker info >/dev/null 2>&1 || die "docker daemon unreachable -- run 'orb start'"
}

running() { [ "$(docker inspect -f '{{.State.Running}}' "${CONTAINER}" 2>/dev/null)" = "true" ]; }

tty_flags() { [ -t 0 ] && printf -- '-it\n' || true; }

# Targets the firewall must prove it drops. Derived, never hardcoded, and every
# one is verified to ANSWER from the host first -- an assertion aimed at a dead
# address passes no matter what the ruleset does, which is worse than no
# assertion at all because it reads as coverage.
blocked_probes() {
  local lan router ts
  lan="$(ipconfig getifaddr en0 2>/dev/null || true)"
  router="$(route -n get default 2>/dev/null | awk '/gateway:/ {print $2; exit}' || true)"
  [ -n "${lan}" ] || die "cannot determine this host's LAN address"
  # This host's own oMLX, by its LAN address: live, and the same service the
  # gateway hole allows. If the container can reach it, the deny list is broken.
  printf '%s:8000\n' "${lan}"
  [ -n "${router}" ] && printf '%s:80\n' "${router}"
  # Only when Tailscale is actually up; a probe against a stopped daemon cannot
  # discriminate and would quietly turn into a no-op.
  if command -v tailscale >/dev/null 2>&1 \
     && [ "$(tailscale status --json 2>/dev/null | jq -r '.BackendState // empty')" = "Running" ]; then
    ts="$(tailscale status --json | jq -r '.TailscaleIPs[]? | select(test(":") | not)' | head -1)"
    [ -n "${ts}" ] && printf '%s:8000\n' "${ts}"
  fi
  return 0
}

prepare_probes() {
  local list target
  list="$(blocked_probes)" || die "cannot build the firewall probe list"
  [ -n "${list}" ] || die "firewall probe list is empty"
  for target in ${list}; do
    curl -s -o /dev/null -m 5 "http://${target}/" \
      || die "probe target ${target} does not answer from this host, so the in-container assertion could never fail"
    log "probe ${target} answers from the host, so it can fail"
  done
  BLOCKED_PROBES="$(printf '%s' "${list}" | tr '\n' ',')"
  BLOCKED_PROBES="${BLOCKED_PROBES%,}"
}

# The agent has arbitrary shell and unrestricted egress, so whatever key it is
# given is a key it can send anywhere. A dedicated oMLX sub-key makes that
# revocable without rotating the one pi and everything else here uses.
warn_shared_key() {
  if [ -n "${OMLX_API_KEY:-}" ] && [ "${ARTIFICIUM_API_KEY}" = "${OMLX_API_KEY}" ]; then
    log "WARNING: using the shared OMLX_API_KEY. An oMLX sub-key would be revocable on its own."
    log "         Note it also reaches /v1/models/{id}/load and /unload, which can disrupt pi."
  fi
}

# Public resolvers are pinned in sandbox_flags so the firewall never has to
# punch a DNS hole to a LAN device it inherited from the host's resolv.conf.
#
# Everything that makes this container a sandbox. Kept in one place so that
# `setup`, `start` and `shell` cannot drift apart on the flags that matter.
# One flag per line, split on the strict-mode IFS at the call site.
sandbox_flags() { sandbox_flags_for "${INSTANCE}"; }

sandbox_flags_for() {
  local instance="$1"
  cat <<FLAGS
--add-host=omlx.host:host-gateway
--cap-drop=ALL
--cap-add=NET_ADMIN
--cap-add=SETUID
--cap-add=SETGID
--cap-add=CHOWN
--cap-add=DAC_OVERRIDE
--cap-add=FOWNER
--security-opt=no-new-privileges
--memory=16g
--memory-swap=16g
--pids-limit=512
--cpus=6
--volume=${instance}:/instance
--volume=${REFERENCE}:/reference:ro
--env=ARTIFICIUM_API_KEY
--env=OMLX_API_KEY
--env=BLOCKED_PROBES=${BLOCKED_PROBES}
--dns=1.1.1.1
--dns=9.9.9.9
FLAGS
}

cmd_build() {
  require_docker
  log "building ${IMAGE} from ${HARNESS}/Dockerfile"
  docker build \
    --build-arg "UID=$(id -u)" \
    --build-arg "GID=$(id -g)" \
    -f "${SANDBOX_DIR}/${HARNESS}/Dockerfile" \
    -t "${IMAGE}" "${SANDBOX_DIR}"
}

# `git archive HEAD` already drops everything gitignored -- nixos/secrets/.env,
# .venv, worktrees. The pathspecs handle the one .env that IS tracked, in
# home-lab: no credentials, but home-network topology all the same.
cmd_export_reference() {
  mkdir -p "${REFERENCE}"
  for entry in "${REFERENCE_REPOS[@]}"; do
    name="${entry%%:*}"
    repo="${entry#*:}"
    [ -d "${repo}/.git" ] || die "not a git repository: ${repo}"
    dest="${REFERENCE}/${name}"
    rm -rf "${dest}"
    mkdir -p "${dest}"
    git -C "${repo}" archive HEAD -- . \
      ':(exclude).env' \
      ':(exclude)**/.env' \
      ':(exclude)secrets/*' \
      ':(exclude)**/secrets/*' \
      | tar -x -C "${dest}"
    log "exported ${name} ($(du -sh "${dest}" | cut -f1 | tr -d ' ')) from $(git -C "${repo}" rev-parse --short HEAD)"
  done
  log "review it before anything runs:  grep -rIl -e 'BEGIN.*PRIVATE KEY' -e 'api[_-]key' ${REFERENCE}"
}



cmd_start() {
  require_docker
  mkdir -p "${INSTANCE}"
  warn_shared_key
  prepare_probes
  if running; then die "${CONTAINER} is already running"; fi
  docker rm -f "${CONTAINER}" >/dev/null 2>&1 || true
  # shellcheck disable=SC2046
  docker run -d --name "${CONTAINER}" $(sandbox_flags) "${IMAGE}"
  log "started; follow it with '${0##*/} logs -f'"
}

cmd_stop() {
  require_docker
  docker stop "${CONTAINER}" >/dev/null && log "stopped ${CONTAINER}"
}

cmd_logs() { require_docker; docker logs "$@" "${CONTAINER}"; }
cmd_status() { require_docker; running || die "${CONTAINER} is not running"
  docker exec -u artificium "${CONTAINER}" hermes kanban list "$@"; }
cmd_show()   { require_docker; running || die "${CONTAINER} is not running"
  docker exec -u artificium "${CONTAINER}" hermes kanban show "$@"; }
cmd_doctor() { require_docker; running || die "${CONTAINER} is not running"
  docker exec -u artificium "${CONTAINER}" hermes doctor; }
cmd_shell() { require_docker; running || die "${CONTAINER} is not running"
  docker exec -itu artificium "${CONTAINER}" bash; }

# Leaves ${RUNS_DIR} alone on purpose: a failed run is only useful if it stays
# inspectable afterwards.
cmd_destroy() {
  require_docker
  docker rm -f "${CONTAINER}" >/dev/null 2>&1 || true
  docker rmi -f "${IMAGE}" >/dev/null 2>&1 || true
  log "removed container and image; ${RUNS_DIR} is untouched"
}

# One bounded question, one profile, no kanban board. `hermes -p X -z "..."` is
# the whole mechanism; everything else this script does is the cage around it.
cmd_task() {
  require_docker
  local dir="${1:-}"; shift || true
  [ -n "${dir}" ] || die "usage: ${0##*/} task <dir> [--minutes N] [--profile NAME]"
  dir="$(cd "${dir}" 2>/dev/null && pwd)" || die "no such directory: ${1:-}"
  [ -f "${dir}/task.md" ] || die "${dir}/task.md not found -- write the task there first"

  local minutes=10 profile=researcher
  while [ $# -gt 0 ]; do
    case "$1" in
      --minutes) minutes="$2"; shift 2 ;;
      --profile) profile="$2"; shift 2 ;;
      *) die "unknown option: $1" ;;
    esac
  done

  [ -n "${ARTIFICIUM_API_KEY}" ] || die "OMLX_API_KEY is not set"
  warn_shared_key
  prepare_probes
  mkdir -p "${dir}/workspace"

  log "task: ${dir}/task.md as ${profile}, ${minutes}m cap"
  # shellcheck disable=SC2046
  docker run --rm $(tty_flags) $(sandbox_flags_for "${dir}") \
    -e AGENT_TASK_MODE=1 \
    "${IMAGE}" bash -c \
    "/usr/local/bin/hermes-bootstrap.sh >/dev/null 2>&1; \
     timeout $(( minutes * 60 )) hermes -p ${profile} -z \"\$(cat /instance/task.md)\""
  log "done; output under ${dir}/workspace/"
}

usage() {
  cat >&2 <<USAGE
usage: ${0##*/} <command> [args]

  build              build the sandbox image
  export-reference   refresh the read-only repo snapshots
  start              run the life-loop in the background
  logs [-f]          the life-loop trace
  status             the kanban board
  show <task_id>     one card with its comments and events
  doctor             hermes doctor inside the container
  shell              a shell in the container, as the agent's user
  stop               stop the life-loop
  task <dir>         run one bounded task from <dir>/task.md (--minutes, --profile)
  destroy            remove the container and image, keep the run directory
USAGE
  exit "${1:-64}"
}

[ $# -ge 1 ] || usage
command="$1"; shift
case "${command}" in
  build)            cmd_build "$@" ;;
  export-reference) cmd_export_reference "$@" ;;
  doctor)           cmd_doctor "$@" ;;
  start)            cmd_start "$@" ;;
  logs)             cmd_logs "$@" ;;
  status)           cmd_status "$@" ;;
  show)             cmd_show "$@" ;;
  shell)            cmd_shell "$@" ;;
  stop)             cmd_stop "$@" ;;
  task)             cmd_task "$@" ;;
  # Internal: bin/agent-verify.sh borrows the exact sandbox flags so the
  # verification runs in the same cage as a real run.
  _flags)           prepare_probes >/dev/null 2>&1; sandbox_flags_for "${1:-${INSTANCE}}" ;;
  destroy)          cmd_destroy "$@" ;;
  -h|--help|help)   usage 0 ;;
  *)                usage ;;
esac
