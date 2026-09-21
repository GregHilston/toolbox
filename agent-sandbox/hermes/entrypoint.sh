#!/bin/bash
# Same contract as the Artificium entrypoint: install the egress firewall as
# root, seed an empty instance, then drop to a non-root user for the rest of the
# container's life. The two harnesses must be caged identically or the
# comparison between them measures the cage.
set -euo pipefail
IFS=$'\n\t'

INSTANCE=/instance
SEED=/opt/agent-seed
RUN_USER=artificium

log() { printf 'entrypoint: %s\n' "$*" >&2; }
die() { printf 'entrypoint: FATAL: %s\n' "$*" >&2; exit 1; }

[ "$(id -u)" -eq 0 ] || die "must start as root to install the firewall"

/usr/local/sbin/init-firewall.sh

refuse_symlink() {
  local path="$1"
  while [ "${path}" != "/" ] && [ "${path}" != "." ]; do
    if [ -L "${path}" ]; then
      die "refusing to write through symlink: ${path}"
    fi
    path="$(dirname "${path}")"
  done
}

refuse_symlink "${INSTANCE}"

# HERMES_HOME and the shared workspace both live on the bind mount, so the board,
# the profiles and the work all survive a restart and are readable from the host.
mkdir -p "${INSTANCE}/home" "${INSTANCE}/workspace"

if [ -d "${SEED}/project" ]; then
  for brief in "${SEED}"/project/*; do
    [ -e "${brief}" ] || continue
    target="${INSTANCE}/workspace/$(basename "${brief}")"
    if [ ! -e "${target}" ]; then
      cp "${brief}" "${target}"
      log "installed $(basename "${brief}")"
    fi
  done
fi

if [ "$(stat -c %U "${INSTANCE}/home")" != "${RUN_USER}" ]; then
  log "taking ownership of ${INSTANCE}"
  chown -R "${RUN_USER}:" "${INSTANCE}"
fi

log "dropping to ${RUN_USER}"
# Without this uv spends 50s retrying PyPI before every failure, and reports a
# connect timeout rather than a missing package. The image's cache carries the
# seeded dependency set; anything else should fail fast and say so.
if [ "${AGENT_OFFLINE:-0}" = "1" ]; then
  export UV_OFFLINE=1
  log "UV_OFFLINE=1 — uv resolves from the image cache only"
fi
exec gosu "${RUN_USER}" "$@"
