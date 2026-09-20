#!/bin/bash
# Apply the egress firewall as root, seed the instance if this is a fresh run,
# then hand the container to a non-root user for the rest of its life.
set -euo pipefail
IFS=$'\n\t'

INSTANCE=/instance
DIST=/opt/artificium-dist
SEED=/opt/artificium-seed
RUN_USER=artificium

log() { printf 'entrypoint: %s\n' "$*" >&2; }

if [ "$(id -u)" -ne 0 ]; then
  echo "entrypoint: FATAL: must start as root to install the firewall" >&2
  exit 1
fi

/usr/local/sbin/init-firewall.sh

# Only ever seeds an empty instance. Everything under /instance is the agent's
# to rewrite, including its own code, and a restart must not undo that.
if [ ! -e "${INSTANCE}/artificium.py" ]; then
  log "seeding a fresh instance from ${DIST}"
  cp -a "${DIST}/." "${INSTANCE}/"
fi

if [ -d "${SEED}" ]; then
  if [ ! -e "${INSTANCE}/mind/self.txt.seeded" ] && [ -e "${SEED}/self.txt" ]; then
    cp "${SEED}/self.txt" "${INSTANCE}/mind/self.txt"
    : > "${INSTANCE}/mind/self.txt.seeded"
    log "installed the standing purpose (Self is mutable from here on)"
  fi
  for brief in "${SEED}"/project/*; do
    [ -e "${brief}" ] || continue
    target="${INSTANCE}/mind/space/vt-smb/$(basename "${brief}")"
    if [ ! -e "${target}" ]; then
      mkdir -p "$(dirname "${target}")"
      cp "${brief}" "${target}"
      log "installed $(basename "${brief}")"
    fi
  done
fi

# Guarded, because a recursive chown over a grown mind/ costs minutes on every
# restart for nothing.
if [ "$(stat -c %U "${INSTANCE}")" != "${RUN_USER}" ]; then
  log "taking ownership of ${INSTANCE}"
  chown -R "${RUN_USER}:${RUN_USER}" "${INSTANCE}"
fi

log "dropping to ${RUN_USER}"
exec gosu "${RUN_USER}" "$@"
