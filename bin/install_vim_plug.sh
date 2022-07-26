#!/bin/bash
set -euo pipefail
IFS=$'\n\t'


echo "Installing vim plug for both vim and nvim..."

# This is to ensure we don't attempt to install oh-my-zsh to /root/, instead we want it to be in a users home directory
./bin/ensure_no_sudo.sh

curl -fLo ~/.vim/autoload/plug.vim --create-dirs \
        https://raw.githubusercontent.com/junegunn/vim-plug/master/plug.vim

sh -c 'curl -fLo "${XDG_DATA_HOME:-$HOME/.local/share}"/nvim/site/autoload/plug.vim --create-dirs \
           https://raw.githubusercontent.com/junegunn/vim-plug/master/plug.vim'
