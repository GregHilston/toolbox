#!/bin/bash
set -euo pipefail
IFS=$'\n\t'

echo "Setting zsh as the default shell..."
chsh -s $(which zsh)

