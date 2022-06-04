#!/bin/bash
set -euo pipefail
IFS=$'\n\t'


echo "Installing vim plug..."

# This is to ensure we don't attempt to install oh-my-zsh to /root/, instead we want it to be in a users home directory
./bin/ensure_no_sudo.sh

curl -fLo ~/.vim/autoload/plug.vim --create-dirs \
        https://raw.githubusercontent.com/junegunn/vim-plug/master/plug.vim
