#!/bin/bash
set -euo pipefail
IFS=$'\n\t'

echo "Installing vim plug plugins..."

# This is to ensure we don't attempt to install oh-my-zsh to /root/, instead we want it to be in a users home directory
./bin/ensure_no_sudo.sh

# From here 
# https://github.com/junegunn/vim-plug/wiki/tips#install-plugins-on-the-command-line
nvim -es -u init.vim -i NONE -c "PlugInstall" -c "qa"
