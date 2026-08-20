#!/usr/bin/env bash
# Refreshes the Reddit session cookie that pi-reddit-research reads.
#
# Reddit has required auth on its .json endpoints since mid-2026, and the
# session cookie expires every few days. Re-pasting it by hand from devtools is
# the kind of chore that silently stops happening, and the failure is quiet: the
# reddit_* tools just start coming back empty.
#
# There is no proper automation available. Reddit's login is interactive
# (password + CAPTCHA + 2FA) and exposes no refresh-token flow, so nothing here
# can *obtain* a session. What it can do is copy one you already have: Firefox
# keeps its cookie jar in an unencrypted SQLite DB on macOS, unlike Chrome and
# Safari which seal theirs with a Keychain key. So as long as you stay logged
# into reddit.com in Firefox, this keeps pi's copy current with no typing.
#
# The tradeoff, stated plainly: this is a *copy*, not a *renew*. If you log out
# of Firefox, clear cookies, or stop visiting Reddit long enough for the session
# to lapse there too, this cannot fix it and will tell you to log in again.
#
# Verified before writing: a reddit_session lifted straight out of Firefox
# authenticates against reddit.com/.json and returns real posts.
set -euo pipefail
IFS=$'\n\t'

# launchd hands agents a bare PATH; sqlite3 and curl are in /usr/bin on macOS,
# but be explicit so this behaves the same when run by hand from a nix shell.
export PATH="/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin:${PATH}"

COOKIE_FILE="${HOME}/.config/pi-reddit-research/cookie.txt"
USER_AGENT="pi-reddit-research/0.1 personal-use (https://www.reddit.com/.json)"
PROBE_URL="https://www.reddit.com/r/NixOS/hot.json?limit=1"

TMPDIR_WORK="$(mktemp -d)"
trap 'rm -rf "${TMPDIR_WORK}"' EXIT

log() { echo "$(date '+%Y-%m-%d %H:%M:%S') $*"; }

# Reaches the phone only if you are at the Mac. Pushover would be better, but
# its token lives in home-lab's secrets on dungeon, not in toolbox's.
notify() {
  osascript -e "display notification \"$1\" with title \"pi: Reddit cookie\"" 2>/dev/null || true
  log "NOTIFY: $1"
}

# Returns 0 if the cookie authenticates. Reddit answers 200 with an empty
# children array when unauthenticated, so checking the status code alone is not
# enough — the post count is the real signal.
probe_cookie() {
  local cookie="$1" out="${TMPDIR_WORK}/probe.json"
  curl -sS -o "${out}" --max-time 20 \
    -H "Cookie: reddit_session=${cookie}" -A "${USER_AGENT}" "${PROBE_URL}" \
    >/dev/null 2>&1 || return 1
  python3 - "${out}" <<'PY'
import json, sys
try:
    with open(sys.argv[1]) as fh:
        data = json.load(fh)
except Exception:
    sys.exit(1)
sys.exit(0 if data.get("data", {}).get("children") else 1)
PY
}

# Firefox holds cookies.sqlite open with WAL, so read a copy — and copy the -wal
# alongside it, or a cookie written since the last checkpoint is invisible.
extract_from_firefox() {
  local db copy
  for db in "${HOME}/Library/Application Support/Firefox/Profiles/"*/cookies.sqlite; do
    [ -f "${db}" ] || continue
    copy="${TMPDIR_WORK}/$(basename "$(dirname "${db}")").sqlite"
    cp "${db}" "${copy}" 2>/dev/null || continue
    if [ -f "${db}-wal" ]; then
      cp "${db}-wal" "${copy}-wal" 2>/dev/null || true
    fi
    # `|| true`: a locked or schema-changed DB must skip this profile, not kill
    # the script — another profile may still have a usable session.
    local value
    value="$(sqlite3 "${copy}" \
      "SELECT value FROM moz_cookies WHERE host='.reddit.com' AND name='reddit_session' LIMIT 1;" 2>/dev/null || true)"
    if [ -n "${value}" ]; then
      printf '%s' "${value}"
      return 0
    fi
  done
  return 1
}

current_cookie() {
  [ -r "${COOKIE_FILE}" ] || return 1
  sed -n 's/.*reddit_session=\([^;]*\).*/\1/p' "${COOKIE_FILE}" | head -1 || true
}

main() {
  local current fresh
  current="$(current_cookie || true)"

  # Cheap exit: if what pi already has still works, changing it can only break
  # things. Firefox may hold an older session than the one pasted by hand.
  if [ -n "${current}" ] && probe_cookie "${current}"; then
    log "OK: existing cookie still authenticates; nothing to do"
    return 0
  fi
  log "existing cookie missing or no longer authenticating; trying Firefox"

  if ! fresh="$(extract_from_firefox)"; then
    notify "No reddit_session in Firefox. Log in at reddit.com in Firefox."
    return 1
  fi

  if [ "${fresh}" = "${current}" ]; then
    notify "Firefox has the same dead cookie. Log in at reddit.com in Firefox again."
    return 1
  fi

  if ! probe_cookie "${fresh}"; then
    notify "Firefox's reddit_session does not authenticate. Log in at reddit.com again."
    return 1
  fi

  # Write via a 600 temp file and mv, so the cookie is never briefly world
  # readable and a crash mid-write cannot leave a truncated file behind.
  mkdir -p "$(dirname "${COOKIE_FILE}")"
  local tmp="${TMPDIR_WORK}/cookie.txt"
  printf 'reddit_session=%s\n' "${fresh}" > "${tmp}"
  chmod 600 "${tmp}"
  mv -f "${tmp}" "${COOKIE_FILE}"
  log "OK: refreshed cookie from Firefox (${#fresh} chars)"
  # pi-reddit-research re-reads cookieFile before every request, so nothing
  # needs restarting — not pi, and not PI WEB's session daemon.
}

main "$@"
