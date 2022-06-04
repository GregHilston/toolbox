#!/bin/bash
set -euo pipefail
IFS=$'\n\t'

echo "Installing vim plug plugins for vim and nvim..."

# This is to ensure we don't attempt to install oh-my-zsh to /root/, instead we want it to be in a users home directory
./bin/ensure_no_sudo.sh

# From here 
# https://github.com/junegunn/vim-plug/wiki/tips#install-plugins-on-the-command-line
vim -es -u vimrc -i NONE -c "PlugInstall" -c "qa"

# The follow commaning supposedly works, from the link above, but was not working.
# Instead I have a new command that's from this link:
# https://github.com/junegunn/vim-plug/issues/675#issuecomment-718089095
#nvim -es -u init.vim -i NONE -c "PlugInstall" -c "qa"
nvim --headless +PlugInstall +qall
