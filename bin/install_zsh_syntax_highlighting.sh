#!/bin/bash
set -euo pipefail
IFS=$'\n\t'

echo "Installing ZSH syntax highlighting..."

export ZSH_CUSTOM=~/.oh-my-zsh/custom


if [ ! -d "$HOME/.oh-my-zsh" ]; then
    echo "Downloading zsh-syntax-highlighting to $ZSH_CUSTOM/plugins/zsh-syntax-highlighting"

    git clone https://github.com/zsh-users/zsh-syntax-highlighting.git $ZSH_CUSTOM/plugins/zsh-syntax-highlighting
else
    echo "Not downloading zsh-syntax highlighting as it already exists in $ZSH_CUSTOM/plugins/zsh-syntax-highlighting"
fi
