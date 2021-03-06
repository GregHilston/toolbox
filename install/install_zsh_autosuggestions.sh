#!/usr/bin/env zsh
set -e

#echo "attemping to source ~/.zshrc will print out after to signal success"
#source ~/.zshrc
#echo "successfully sourced ~/.zshrc"

#if [[ -z "${ZSH_CUSTOM}" ]]; then
#  echo "the environment variable ZSH_CUSTOM is not defined, can't install zsh-autosuggestion"
#  exit -1
#fi

# Need to install the zsh-autosuggestions ourselves, no longer shipped
# used https://gist.github.com/dogrocker/1efb8fd9427779c827058f873b94df95
# and http://www.geekmind.net/2011/08/how-to-reload-your-zshrc.html
# and https://stackoverflow.com/questions/36498981/shell-dont-fail-if-git-clone-if-folder-already-exists
echo "zsh-autosuggestions being cloned or updated at path $ZSH/plugins/zsh-autosuggestions"

if [ ! -d "$ZSH/plugins/zsh-autosuggestions" ] ; then
    echo "attempting to clone to $ZSH_CUSTOM/plugins/zsh-autosuggestions"
    git clone https://github.com/zsh-users/zsh-autosuggestions.git $ZSH/plugins/zsh-autosuggestions
else 
    echo "attempting to update $ZSH_CUSTOM/plugins/zsh-autosuggestions"
    pushd "$ZSH/plugins/zsh-autosuggestions"
    git pull origin master
fi
zsh -c "source ~/.zshrc"
