#!/bin/bash
set -euo pipefail
IFS=$'\n\t'

./install/helper_ensure_no_sudo.sh

sudo ./install/install_essential_on_bare_bones.sh

sudo ./install/install_bare_minimum.sh

sudo ./install/install_zsh.sh

sudo ./install/install_oh_my_zsh.sh

sudo ./install/backup_dot_files.sh

sudo ./install/install_dots.sh

# TODO investigate why may get output [oh-my-zsh] plugin 'zsh-syntax-highlighting' not found
sudo ./install/install_zsh_autosuggestions.sh

sudo ./install/install_vim_plug.sh

# TODO might need to source ~/.zshrc before running this
echo "Installing vim plugins..."
sudo vim +PlugInstall +qall

echo "Installation of toolbox was potentially success!\nLogout and log back in, then run again to be sure. This is so ZSH will be your default shell and will source the ~/.zshrc file.";
