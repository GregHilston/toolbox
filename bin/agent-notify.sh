#!/bin/bash
# Push one line of run news to a phone, over whichever transports are configured.
#
# The harness called `pushover.py` directly from two places. Pushover is fine for
# "the run ended" but it is one-way, so answering "how is it going" still meant
# opening a laptop. Telegram's bot API is a long poll, which our default-deny
# firewall already permits outbound, so the same credential carries alerts out
# and commands in -- see `agent-telegram.py`, which owns the inbound half.
#
# Each transport no-ops when unconfigured rather than erroring, so a host with
# only Pushover set up keeps working untouched. Exit 0 means at least one
# transport delivered; callers treat that as advisory.
#
# This speaks the Telegram HTTP API itself rather than calling agent-telegram.py,
# so an alert still goes out when the bot is not installed or its loop is wedged.
set -uo pipefail
IFS=$'\n\t'

TOOLBOX="${TOOLBOX:-$HOME/Git/toolbox}"
ENV_FILE="${AGENT_NOTIFY_ENV:-${TOOLBOX}/nixos/secrets/.env}"
TRANSPORT="${AGENT_NOTIFY_TRANSPORT:-both}"

msg=""
while [ $# -gt 0 ]; do
  case "$1" in
    -m|--message) msg="${2:-}"; shift 2 ;;
    -t|--transport) TRANSPORT="${2:-}"; shift 2 ;;
    -h|--help) sed -n '2,12p' "$0"; exit 0 ;;
    *) echo "unknown argument: $1" >&2; exit 64 ;;
  esac
done
[ -n "${msg}" ] || msg="$(cat)"
[ -n "${msg}" ] || { echo "usage: ${0##*/} -m <message>" >&2; exit 64; }

log() { printf '==> %s\n' "$*" >&2; }

# launchd hands an agent none of the shell's environment, so the secrets file is
# the only place the token reliably is. A shell that already sourced it wins.
if [ -z "${TELEGRAM_BOT_TOKEN:-}" ] && [ -r "${ENV_FILE}" ]; then
  set -a; . "${ENV_FILE}"; set +a
fi

sent=0

case "${TRANSPORT}" in both|pushover)
  if [ -n "${PUSHOVER_USER_KEY:-}" ] && [ -n "${PUSHOVER_WORK_API_KEY:-}" ]; then
    if "${TOOLBOX}/bin/pushover.py" -m "${msg}" >/dev/null 2>&1; then
      sent=$(( sent + 1 )); log "pushover: sent"
    else
      log "pushover: FAILED"
    fi
  fi
esac

case "${TRANSPORT}" in both|telegram)
  if [ -n "${TELEGRAM_BOT_TOKEN:-}" ] && [ -n "${TELEGRAM_CHAT_ID:-}" ]; then
    # No parse_mode: a verdict carries file paths and run names, and Telegram
    # rejects the whole message when it cannot parse their underscores.
    if curl -sS -m 20 -o /dev/null -w '%{http_code}' \
         "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
         --data-urlencode "chat_id=${TELEGRAM_CHAT_ID}" \
         --data-urlencode "text=${msg:0:4000}" 2>/dev/null | grep -q '^200$'; then
      sent=$(( sent + 1 )); log "telegram: sent"
    else
      log "telegram: FAILED"
    fi
  fi
esac

[ "${sent}" -gt 0 ] || { log "no transport configured (${TRANSPORT})"; exit 1; }
