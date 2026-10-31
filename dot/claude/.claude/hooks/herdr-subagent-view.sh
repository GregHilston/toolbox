#!/bin/sh
# Prints a subagent's transcript as readable lines, for its Herdr tab.
tail -n +1 -F "$1" 2>/dev/null | jq -r --unbuffered '
  select(.type == "assistant") | .message.content[]? |
  if .type == "text" then .text
  elif .type == "tool_use" then "> \(.name) \(.input.command // .input.file_path // .input.pattern // .input.description // "")"
  else empty end'
