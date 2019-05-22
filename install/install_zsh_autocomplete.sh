#!/usr/bin/env zsh
set -e

source ~/.zshrc

if [[ -z "${ZSH_CUSTOM}" ]]; then
  echo "the environment variable ZSH_CUSTOM is not defined, can't install zsh-autosuggestion"
  exit -1
fi

# Need to install the zsh-autosuggestions ourselves, no longer shipped
# used https://gist.github.com/dogrocker/1efb8fd9427779c827058f873b94df95
# and http://www.geekmind.net/2011/08/how-to-reload-your-zshrc.html
# and https://stackoverflow.com/questions/36498981/shell-dont-fail-if-git-clone-if-folder-already-exists
if [ ! -d "$ZSH_CUSTOM/plugins/zsh-autosuggestions" ] ; then
    # echo "attempting to clone to $ZSH_CUSTOM/plugins/zsh-autosuggestions"
    git clone https://github.com/zsh-users/zsh-autosuggestions.git $ZSH_CUSTOM/plugins/zsh-autosuggestions
else 
    # echo "attempting to update $ZSH_CUSTOM/plugins/zsh-autosuggestions"
    pushd "$ZSH_CUSTOM/plugins/zsh-autosuggestions"
    git pull origin master
fi
zsh -c "source ~/.zshrc"
