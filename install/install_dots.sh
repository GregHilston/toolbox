#!/bin/bash
set -euo pipefail
IFS=$'\n\t'

echo "Installing dot files..."

SCRIPT_HOME=$(cd "$(dirname $0)" && pwd)
TOOLBOX_HOME=$(echo $SCRIPT_HOME | rev | cut -d/ -f2- | rev)
HOME=$($SCRIPT_HOME/helper_get_home_directory.sh)

INSTALL=(bashrc gitignore tmux.conf vimrc zshrc env vim)

# nvim (special case)
echo -e "Creating nvim config folder if it doesn't exist..."
mkdir -p ~/.config/nvim
echo -e "Installing nvim config..."
ln -sf "$TOOLBOX_HOME/dot/config/nvim/init.vim" "$HOME/.config/nvim/init.vim"

# i3 (special case)
echo -e "Creating i3 config folder if it doesn't exist"
mkdir -p ~/.i3
echo -e "Installing i3 config..."
echo -e " \t linking $HOME/.i3/config to $TOOLBOX_HOME/dot/i3/config ..."
ln -sf "$TOOLBOX_HOME/dot/i3/config" "$HOME/.i3/config"
echo "reload i3 with \$mod + shift + r"
echo " Done"

#echo -e "creating directory needed for vim-plug"
#if [ ! -e ~/.vim ]; then
#  echo "HERE"
#  mkdir -p ~/.vim/autoload
#fi

# I havent figure dout if this is needed, commenting out but leaving here for now
# echo -e "install vim-plug plugins"
# rm -rf ~/.vim
# vim +PlugInstall +qall

for install in "${INSTALL[@]}"; do
  echo -e "Installing $install... "

  echo -e ' \t removing old symbolic link..'
  rm -rf ~/.$install

  echo -e " \t linking $HOME/.$install to $TOOLBOX_HOME/dot/$install ..."
  ln -s "$TOOLBOX_HOME/dot/$install" "$HOME/.$install"

  echo " Done"
done


printf "Install gnzh_customized_by_grehg manually by symbolically linking, ⚠️  this requires oh-my-zsh to have already been installed ..."
ln -sf $TOOLBOX_HOME/dot/zsh-custom/themes/gnzh_customized_by_grehg.zsh-theme ~/.oh-my-zsh/themes/gnzh_customized_by_grehg.zsh-theme
echo " Done"

printf "Linking bin and lib... "
rm -rf "$HOME/.bin"
rm -rf "$HOME/.lib"
ln -s "$TOOLBOX_HOME/bin" "$HOME/.bin"
ln -s "$TOOLBOX_HOME/lib" "$HOME/.lib"
echo " Done"
