#!/bin/bash
# Need to install the zsh-autosuggestions ourselves, no longer shipped
# used https://gist.github.com/dogrocker/1efb8fd9427779c827058f873b94df95
# and http://www.geekmind.net/2011/08/how-to-reload-your-zshrc.html
# and https://stackoverflow.com/questions/36498981/shell-dont-fail-if-git-clone-if-folder-already-exists
if [ ! -d "$ZSH_CUSTOM/plugins/zsh-autosuggestions" ] ; then
    sudo git clone https://github.com/zsh-users/zsh-autosuggestions.git $ZSH_CUSTOM/plugins/zsh-autosuggestions
else
    pushd "$ZSH_CUSTOM/plugins/zsh-autosuggestions"
    git pull origin master
fi
zsh -c "source ~/.zshrc"