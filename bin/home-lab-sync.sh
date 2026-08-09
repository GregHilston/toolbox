#!/usr/bin/env bash
# Clones or fast-forwards ~/Git/home-lab on dungeon.
#
# dungeon needs this repo checked out at runtime (the NFS stale-handle watchdog
# runs scripts/nfs-stale-check.sh out of it). This used to live in dungeon's
# nix-darwin postActivation, which was the wrong layer three ways: it ran as
# root and had to trampoline back through `sudo -H -u`, it needed an SSH
# pre-flight probe because root has no access to the user's ssh-agent, and a
# missing GitHub key would `exit 1` and abort the rest of activation.
#
# As a launchd *user* agent it just runs as the user, so the ssh-agent is
# already there and none of that scaffolding is needed. A failure here is
# logged and ignored — it must never be able to break `darwin-rebuild switch`.
set -uo pipefail

# launchd hands agents a bare PATH (/usr/bin:/bin:/usr/sbin:/sbin), so make sure
# the nix and Homebrew git are reachable before falling back to /usr/bin/git.
export PATH="/run/current-system/sw/bin:/opt/homebrew/bin:${PATH}"

REPO_DIR="${HOME}/Git/home-lab"
REMOTE="${HOME_LAB_REMOTE:-git@github.com:GregHilston/home-lab.git}"

log() { echo "[home-lab-sync $(date '+%Y-%m-%dT%H:%M:%S')] $*"; }

mkdir -p "${HOME}/Git"

if [ -d "$REPO_DIR/.git" ]; then
  log "pulling $REPO_DIR"
  # --ff-only: never create a merge commit behind the user's back. If local
  # work has diverged this fails loudly in the log and leaves the tree alone.
  if git -C "$REPO_DIR" pull --ff-only; then
    log "up to date"
  else
    log "WARNING: pull failed (diverged branch, or no GitHub SSH access)"
  fi
else
  log "cloning into $REPO_DIR"
  if git clone "$REMOTE" "$REPO_DIR"; then
    log "cloned"
  else
    log "WARNING: clone failed — check GitHub SSH access (ssh -T git@github.com)"
  fi
fi
