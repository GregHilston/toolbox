#!/bin/bash
set -euo pipefail
IFS=$'\n\t'

echo "Installing bare minimum..."
apt-get update && apt-get install tmux curl vim neovim fzf ripgrep tree -y
