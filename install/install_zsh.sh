#!/bin/bash
set -e

echo "installing zsh..."
sudo apt-get install zsh -y
exit 

echo "setting zsh as the default shell..."
chsh -s $(which zsh)

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
