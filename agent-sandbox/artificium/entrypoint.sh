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
die() { printf 'entrypoint: FATAL: %s\n' "$*" >&2; exit 1; }

[ "$(id -u)" -eq 0 ] || die "must start as root to install the firewall"

/usr/local/sbin/init-firewall.sh

# Everything under /instance belongs to the agent between runs, so root must not
# be tricked into writing through a symlink it planted. Nothing here writes
# agent-controlled bytes, so the worst case is a wedged container -- but the
# guard is two lines.
refuse_symlink() {
  local path="$1"
  while [ "${path}" != "/" ] && [ "${path}" != "." ]; do
    if [ -L "${path}" ]; then
      die "refusing to write through symlink: ${path}"
    fi
    path="$(dirname "${path}")"
  done
}

refuse_symlink "${INSTANCE}/artificium.py"

seeded=false
if [ ! -f "${INSTANCE}/artificium.py" ]; then
  log "seeding a fresh instance from ${DIST}"
  cp -a "${DIST}/." "${INSTANCE}/"
  seeded=true
fi

# Self is installed by `setup --self-file`, not here, so there is exactly one
# mechanism for it and no marker file left lying around inside mind/.
if [ -d "${SEED}/project" ]; then
  for brief in "${SEED}"/project/*; do
    [ -e "${brief}" ] || continue
    target="${INSTANCE}/mind/space/vt-smb/$(basename "${brief}")"
    if [ ! -e "${target}" ]; then
      refuse_symlink "$(dirname "${target}")"
      mkdir -p "$(dirname "${target}")"
      cp "${brief}" "${target}"
      log "installed $(basename "${brief}")"
    fi
  done
fi

# Guarded on a path the seed created, not on the bind-mount root: the mount root
# may already read as the host user while everything root just copied into it
# does not. A recursive chown over a grown mind/ costs minutes, so it runs when
# the seed ran and otherwise only if ownership actually looks wrong.
#
# `${RUN_USER}:` means "the user's own login group" -- there may be no group
# named artificium, since GID 20 is already dialout on Debian.
if [ "${seeded}" = true ] || [ "$(stat -c %U "${INSTANCE}/artificium.py")" != "${RUN_USER}" ]; then
  log "taking ownership of ${INSTANCE}"
  chown -R "${RUN_USER}:" "${INSTANCE}"
fi

log "dropping to ${RUN_USER}"
exec gosu "${RUN_USER}" "$@"
