#!/bin/bash
# Build, seed and drive the sandboxed Artificium run. See artificium/CLAUDE.md.
set -euo pipefail
IFS=$'\n\t'

IMAGE="${ARTIFICIUM_IMAGE:-artificium-sandbox:latest}"
CONTAINER="${ARTIFICIUM_CONTAINER:-artificium-vt-smb}"
RUNS_DIR="${ARTIFICIUM_RUNS_DIR:-$HOME/Git/artificium-runs}"
INSTANCE="${RUNS_DIR}/vt-smb/instance"
REFERENCE="${RUNS_DIR}/reference"
DOCKERFILE_DIR="${ARTIFICIUM_HOME:-$HOME/Git/toolbox/artificium}"

MODEL="${ARTIFICIUM_MODEL:-Qwen3.6-35B-A3B-4bit-DWQ}"
CONTEXT_WINDOW="${ARTIFICIUM_CONTEXT_WINDOW:-131072}"
WORKING_MEMORY="${ARTIFICIUM_WORKING_MEMORY:-96000}"

# Exported, not passed on the command line: `--env=NAME` reads it from this
# process, so the key never shows up in `ps` on the host.
export ARTIFICIUM_API_KEY="${ARTIFICIUM_API_KEY:-${OMLX_API_KEY:-}}"

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

# Everything that makes this container a sandbox. Kept in one place so that
# `setup`, `start` and `shell` cannot drift apart on the flags that matter.
# One flag per line, split on the strict-mode IFS at the call site.
sandbox_flags() {
  cat <<FLAGS
--add-host=omlx.host:host-gateway
--cap-drop=ALL
--cap-add=NET_ADMIN
--cap-add=NET_RAW
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
--volume=${INSTANCE}:/instance
--volume=${REFERENCE}:/reference:ro
--env=ARTIFICIUM_API_KEY
FLAGS
}

cmd_build() {
  require_docker
  log "building ${IMAGE}"
  docker build \
    --build-arg "UID=$(id -u)" \
    --build-arg "GID=$(id -g)" \
    -t "${IMAGE}" "${DOCKERFILE_DIR}"
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
    log "exported ${name} ($(du -sh "${dest}" | cut -f1)) from $(git -C "${repo}" rev-parse --short HEAD)"
  done
  log "review it before anything runs:  grep -rIl -e 'BEGIN.*PRIVATE KEY' -e 'api[_-]key' ${REFERENCE}"
}

cmd_setup() {
  require_docker
  [ -d "${REFERENCE}" ] || die "run 'export-reference' first"
  [ -n "${ARTIFICIUM_API_KEY}" ] || die "OMLX_API_KEY is not set -- run 'just secrets' in nixos/ and open a new shell"
  mkdir -p "${INSTANCE}"

  log "configuring against ${MODEL}"
  # shellcheck disable=SC2046 # deliberate word splitting of the flag list
  docker run --rm $(tty_flags) $(sandbox_flags) "${IMAGE}" \
    python3 /instance/artificium.py setup \
      --provider custom \
      --adapter openai_compatible \
      --url "http://omlx.host:8000/v1" \
      --model "${MODEL}" \
      --context-window "${CONTEXT_WINDOW}" \
      --working-memory-tokens "${WORKING_MEMORY}" \
      --mandatory-offload on \
      --offload-threshold 80 \
      --auto-repair on \
      --reasoning auto \
      --request-timeout off \
      --self-file /opt/artificium-seed/self.txt \
      --yes \
      --no-launch
}

cmd_doctor() {
  require_docker
  # shellcheck disable=SC2046
  docker run --rm $(tty_flags) $(sandbox_flags) "${IMAGE}" \
    python3 /instance/artificium.py doctor --live
}

cmd_start() {
  require_docker
  [ -f "${INSTANCE}/artificium-code/config.json" ] || die "not configured -- run 'setup' first"
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
  docker exec -u artificium "${CONTAINER}" python3 /instance/artificium.py status "$@"; }
cmd_watch() { require_docker; running || die "${CONTAINER} is not running"
  docker exec -itu artificium "${CONTAINER}" python3 /instance/artificium.py watch "$@"; }
cmd_chat() { require_docker; running || die "${CONTAINER} is not running"
  docker exec -itu artificium "${CONTAINER}" python3 /instance/artificium.py chat "$@"; }
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

usage() {
  cat >&2 <<USAGE
usage: ${0##*/} <command> [args]

  build              build the sandbox image
  export-reference   refresh the read-only repo snapshots
  setup              configure the instance against oMLX (needs OMLX_API_KEY)
  doctor             send one full harness request and report what came back
  start              run the life-loop in the background
  logs [-f]          the life-loop trace
  status [--json]    runtime summary
  watch              attach to the trace
  chat               talk to the agent
  shell              a shell in the container, as the agent's user
  stop               stop the life-loop
  destroy            remove the container and image, keep the run directory
USAGE
  exit 64
}

[ $# -ge 1 ] || usage
command="$1"; shift
case "${command}" in
  build)            cmd_build "$@" ;;
  export-reference) cmd_export_reference "$@" ;;
  setup)            cmd_setup "$@" ;;
  doctor)           cmd_doctor "$@" ;;
  start)            cmd_start "$@" ;;
  logs)             cmd_logs "$@" ;;
  status)           cmd_status "$@" ;;
  watch)            cmd_watch "$@" ;;
  chat)             cmd_chat "$@" ;;
  shell)            cmd_shell "$@" ;;
  stop)             cmd_stop "$@" ;;
  destroy)          cmd_destroy "$@" ;;
  *)                usage ;;
esac
