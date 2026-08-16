#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

# localclaude — run Claude Code against the local oMLX server.
#
# Requires oMLX to be running (launchd agent org.nixos.omlx, port 8000). On
# moria that is local; other hosts point at dungeon, which serves the low-power
# clients. See the toolbox CLAUDE.md -> "oMLX" and modules/darwin/omlx.nix.
#
# The default model is the Qwen MoE rather than Gemma: model_settings.json
# tunes Gemma for summarization/RAG with thinking disabled, which is the wrong
# shape for a coding agent. Override either value from the environment:
#
#   OMLX_MODEL=gemma-4-26b-a4b-it-qat-4bit localclaude
#   OMLX_BASE_URL=http://dungeon:8000/v1 localclaude
#
# Model names must match the keys in dot/omlx/.omlx/model_settings.json.

OMLX_BASE_URL="${OMLX_BASE_URL:-http://localhost:8000/v1}"
OMLX_MODEL="${OMLX_MODEL:-Qwen3.6-35B-A3B-8bit}"

# Normalise so the health check works whether the override ends in /v1, /v1/,
# or neither: strip any trailing slash first, then a trailing /v1.
_root="${OMLX_BASE_URL%/}"
_root="${_root%/v1}"

# Fail with a useful message rather than letting Claude Code retry a dead port.
if ! curl -fsS --max-time 3 "$_root/v1/models" >/dev/null 2>&1; then
  echo "localclaude: no oMLX server responding at $OMLX_BASE_URL" >&2
  echo "  Start it:  launchctl kickstart -k \"gui/\$(id -u)/org.nixos.omlx\"" >&2
  echo "  Or point elsewhere:  OMLX_BASE_URL=http://dungeon:8000/v1 localclaude" >&2
  exit 1
fi

exec env \
  ANTHROPIC_BASE_URL="$OMLX_BASE_URL" \
  ANTHROPIC_AUTH_TOKEN="omlx" \
  CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1 \
  claude --model "$OMLX_MODEL" "$@"
