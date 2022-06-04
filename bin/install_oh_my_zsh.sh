#!/bin/bash
set -euo pipefail
IFS=$'\n\t'

echo "Installing oh my zsh..."

# This is to ensure we don't attempt to install oh-my-zsh to /root/, instead we want it to be in a users home directory
./bin/ensure_no_sudo.sh

if [ ! -d "$HOME/.oh-my-zsh" ]; then
    echo "Downloading oh-my-zsh, as it hasn't been installed yet"

    sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)" "" --unattended
else
    echo "Not re-downloading or installing, as $HOME/.oh-my-zsh already exists..."
fi
