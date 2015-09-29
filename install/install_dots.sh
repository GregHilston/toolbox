#!/usr/bin/env bash
set -e

SCRIPT_HOME=$(cd "$(dirname $0)" && pwd)
TOOLBOX_HOME=$(echo $SCRIPT_HOME | rev | cut -d/ -f2- | rev)

INSTALL=(bashrc gitignore tmux.conf vimrc zshrc env vim oh-my-zsh)

for install in "${INSTALL[@]}"; do
  printf "Installing $install"
  ln -f -s $TOOLBOX_HOME/dots/$install ~/.$install
  printf "..."
  echo " Done"
done

chsh -s /bin/zsh
