#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

# localclaude — run Claude Code against the local oMLX server.
#
# Requires oMLX to be running (launchd agent org.nixos.omlx, port 8000). On
# moria that is local; other hosts point at dungeon, which serves the low-power
# clients. See the toolbox CLAUDE.md -> "oMLX" and modules/darwin/omlx.nix.
#
# oMLX verifies API keys (skip_api_key_verification is false in settings.json),
# so $OMLX_API_KEY is required. It is auto-loaded into every shell from
# nixos/secrets/.env; if it's missing, run `just secrets` in nixos/ and open a
# new terminal.
#
# The default model is the Qwen MoE rather than Gemma: model_settings.json
# tunes Gemma for summarization/RAG with thinking disabled, which is the wrong
# shape for a coding agent. Override any of these from the environment:
#
#   OMLX_MODEL=gemma-4-26b-a4b-it-qat-4bit localclaude
#   OMLX_BASE_URL=http://dungeon:8000/v1 localclaude
#   OMLX_TIMEOUT=30 localclaude          # slow link, or a cold model load
#
# Model names must match the keys in dot/omlx/.omlx/model_settings.json.

OMLX_BASE_URL="${OMLX_BASE_URL:-http://localhost:8000/v1}"
OMLX_MODEL="${OMLX_MODEL:-Qwen3.6-35B-A3B-8bit}"
# Generous by default: a cold oMLX loading a 35B MoE, or dungeon over Tailscale,
# takes well over a couple of seconds to answer /v1/models.
OMLX_TIMEOUT="${OMLX_TIMEOUT:-15}"

if [[ -z "${OMLX_API_KEY:-}" ]]; then
  echo "localclaude: OMLX_API_KEY is not set." >&2
  echo "  Run \`just secrets\` in ~/Git/toolbox/nixos, then open a new terminal." >&2
  exit 1
fi

# Normalise the override so both the probe and the exec get the canonical
# .../v1 shape, whether the caller passed /v1, /v1/, a trailing slash, or none.
_root="${OMLX_BASE_URL%/}"
_root="${_root%/v1}"
OMLX_BASE_URL="$_root/v1"

# Fail with a useful message rather than letting Claude Code retry a dead port.
# The probe is authenticated: unauthenticated /v1/models returns 401, which
# `curl -f` reports as a failure even though the server is perfectly healthy.
if ! curl -fsS --max-time "$OMLX_TIMEOUT" \
  -H "Authorization: Bearer $OMLX_API_KEY" \
  "$OMLX_BASE_URL/models" >/dev/null 2>&1; then
  echo "localclaude: no healthy oMLX server at $OMLX_BASE_URL" >&2
  echo "  Start it:   launchctl kickstart -k \"gui/\$(id -u)/org.nixos.omlx\"" >&2
  echo "  Elsewhere:  OMLX_BASE_URL=http://dungeon:8000/v1 localclaude" >&2
  echo "  Slow link:  OMLX_TIMEOUT=60 localclaude" >&2
  echo "  (A 401 here means the server is up but OMLX_API_KEY is stale.)" >&2
  exit 1
fi

exec env \
  ANTHROPIC_BASE_URL="$OMLX_BASE_URL" \
  ANTHROPIC_AUTH_TOKEN="$OMLX_API_KEY" \
  CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1 \
  claude --model "$OMLX_MODEL" "$@"
