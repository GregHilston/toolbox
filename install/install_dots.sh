#!/usr/bin/env bash
set -e

SCRIPT_HOME=$(cd "$(dirname $0)" && pwd)
TOOLBOX_HOME=$(echo $SCRIPT_HOME | rev | cut -d/ -f2- | rev)
HOME=$($SCRIPT_HOME/helper_get_home_directory.sh)

INSTALL=(bashrc gitignore tmux.conf vimrc zshrc env vim oh-my-zsh zsh-custom)

# special case
echo -e "Creating i3 config folder if it doesn't exist"
mkdir -p ~/.i3
echo -e "Installing i3 config..."
echo -e ' \t removing old symbolic link..'
rm -rf ~/.i3/config
echo -e " \t linking $HOME/.i3/config to $TOOLBOX_HOME/dots/i3/config ..."
ln -s "$TOOLBOX_HOME/dots/i3/config" "$HOME/.i3/config"
echo "reload i3 with \$mod + shift + r"
echo " Done"

for install in "${INSTALL[@]}"; do
  echo -e "Installing $install... "

  echo -e ' \t removing old symbolic link..'
  rm -rf ~/.$install

  echo -e " \t linking $HOME/.$install to $TOOLBOX_HOME/dots/$install ..."
  ln -s "$TOOLBOX_HOME/dots/$install" "$HOME/.$install"

  echo " Done"
done

printf "Installing gnzh_customized_by_grehg... "
ln -sf "$TOOLBOX_HOME/dots/zsh-custom/themes/gnzh_customized_by_grehg.zsh-theme" "$HOME/.oh-my-zsh/themes/gnzh_customized_by_grehg.zsh-theme"
echo " Done"

printf "Installing gnzh_customized_by_grehg... "
ln -sf "$TOOLBOX_HOME/dots/zsh-custom/themes/gnzh_customized_by_grehg.zsh-theme" "$TOOLBOX_HOME/dots/"
echo " Done"

printf "Linking bin and lib... "
rm -rf "$HOME/.bin"
rm -rf "$HOME/.lib"
ln -s "$TOOLBOX_HOME/bin" "$HOME/.bin"
ln -s "$TOOLBOX_HOME/lib" "$HOME/.lib"
echo " Done"
