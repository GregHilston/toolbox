#!/usr/bin/env bash
set -euo pipefail

# localclaude — run Claude Code against a local LM Studio model.
#
# Defaults to the same model Roger uses (Gemma 4), but you can override:
#   localclaude --model google/gemma-3-27b-it
#   localclaude --model qwen/qwen2.5-coder-32b-instruct
#
# Requires LM Studio to be running with the server enabled (port 1234).

LMSTUDIO_BASE_URL="${LMSTUDIO_BASE_URL:-http://localhost:1234/v1}"
LMSTUDIO_MODEL="${LMSTUDIO_MODEL:-google/gemma-4-26b-a4b}"

exec env \
  ANTHROPIC_BASE_URL="$LMSTUDIO_BASE_URL" \
  ANTHROPIC_AUTH_TOKEN="lm-studio" \
  CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1 \
  claude --model "$LMSTUDIO_MODEL" "$@"
