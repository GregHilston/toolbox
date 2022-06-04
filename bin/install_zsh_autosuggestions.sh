#!/bin/bash
set -euo pipefail
IFS=$'\n\t'

echo "Installing zsh autosuggestions"

# This is to ensure we don't attempt to install oh-my-zsh to /root/, instead we want it to be in a users home directory
./bin/ensure_no_sudo.sh

#echo "attemping to source ~/.zshrc will print out after to signal success"
#source ~/.zshrc
#echo "successfully sourced ~/.zshrc"

#if [[ -z "${ZSH_CUSTOM}" ]]; then
#  echo "the environment variable ZSH_CUSTOM is not defined, can't install zsh-autosuggestion"
#  exit -1
#fi

# setting $ZSH and $ZSH_CUSTOM to where i think it should be installed not sure why this is needed
export ZSH=~/.oh-my-zsh
export ZSH_CUSTOM=~/.oh-my-zsh/custom

# Need to install the zsh-autosuggestions ourselves, no longer shipped
# used https://gist.github.com/dogrocker/1efb8fd9427779c827058f873b94df95
# and http://www.geekmind.net/2011/08/how-to-reload-your-zshrc.html
# and https://stackoverflow.com/questions/36498981/shell-dont-fail-if-git-clone-if-folder-already-exists

if [ ! -d "$ZSH/plugins/zsh-autosuggestions" ] ; then
    echo "Cloning or updating zsh-autosuggestions to path $ZSH/plugins/zsh-autosuggestions"

    echo "Attempting to clone to $ZSH_CUSTOM/plugins/zsh-autosuggestions"
    git clone https://github.com/zsh-users/zsh-autosuggestions.git $ZSH/plugins/zsh-autosuggestions
else 
    echo "Attempting to update $ZSH_CUSTOM/plugins/zsh-autosuggestions"
    pushd "$ZSH/plugins/zsh-autosuggestions"
    git pull origin master
fi

