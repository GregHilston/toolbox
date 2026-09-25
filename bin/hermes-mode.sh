#!/usr/bin/env bash
# Point every Hermes bot at local models, DeepSeek, or the measured mix.
#
#   hermes-mode.sh local|mixed|cloud   # switch and remember
#   hermes-mode.sh                     # re-apply the saved mode
#
# Each profile's config.yaml reads ${MODEL_*}, ${JUDGE_*} and ${UTIL_*}, which a
# profile resolves from its OWN .env, so one variable name can mean a different
# model per role. This rewrites those lines in every .env. Bot profiles pick the
# change up on their next message; the default profile needs a gateway restart.
set -euo pipefail

H="${HERMES_HOME:-${HOME}/.hermes}"
OMLX=http://127.0.0.1:8000/v1
DEEPSEEK=https://api.deepseek.com/v1

has_deepseek() { grep -q '^DEEPSEEK_API_KEY=.' "${H}/.env" 2>/dev/null; }
default_mode() { if has_deepseek; then echo mixed; else echo local; fi; }
mode="${1:-$(cat "${H}/mode" 2>/dev/null || default_mode)}"

# provider model base_url key-variable
worker_local="custom Qwen3.6-35B-A3B-4bit-DWQ ${OMLX} OMLX_API_KEY"
judge_local="custom Qwen3.8-27B-4bit ${OMLX} OMLX_API_KEY"
cloud="deepseek deepseek-flash ${DEEPSEEK} DEEPSEEK_API_KEY"

# worker: builder, researcher, librarian, default. judge: orchestrator, reviewer,
# goal judges, planner. util: triage rewrites and compression.
case "${mode}" in
  local) worker="${worker_local}" judge="${judge_local}" util="${judge_local}" ;;
  mixed) worker="${worker_local}" judge="${cloud}"       util="${judge_local}" ;;
  cloud) worker="${cloud}"        judge="${cloud}"       util="${cloud}" ;;
  *) sed -n '2,5p' "$0" >&2; exit 64 ;;
esac

block() {  # <env-file> <prefix> <spec>
  local provider model url keyvar key
  read -r provider model url keyvar <<< "$3"
  # A .env value is not interpolated, so the key is copied in, not referenced.
  key="$(grep "^${keyvar}=" "$1" | tail -1 | cut -d= -f2-)"
  [ -n "${key}" ] || { echo "${1}: no ${keyvar}, so mode ${mode} cannot work here" >&2; exit 1; }
  printf '%s_PROVIDER=%s\n%s_NAME=%s\n%s_BASE_URL=%s\n%s_API_KEY=%s\n' \
    "$2" "${provider}" "$2" "${model}" "$2" "${url}" "$2" "${key}"
}

for env in "${H}/.env" "${H}"/profiles/*/.env; do
  [ -f "${env}" ] || continue
  case "$(basename "$(dirname "${env}")")" in
    orchestrator|reviewer) own="${judge}" ;;
    *) own="${worker}" ;;
  esac
  tmp="$(mktemp)"
  grep -v -E '^(# hermes-mode|(MODEL|JUDGE|UTIL)_)' "${env}" > "${tmp}" || true
  {
    cat "${tmp}"
    echo "# hermes-mode ${mode}"
    block "${env}" MODEL "${own}"
    block "${env}" JUDGE "${judge}"
    block "${env}" UTIL "${util}"
  } > "${tmp}.new"
  chmod 600 "${tmp}.new"
  mv "${tmp}.new" "${env}"
  rm -f "${tmp}"
done

echo "${mode}" > "${H}/mode"
echo "hermes: ${mode}. Restart the gateway for the default profile: hermes gateway restart"
