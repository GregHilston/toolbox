#!/bin/bash
set -euo pipefail
IFS=$'\n\t'

./bin/ensure_no_sudo.sh

sudo ./bin/install_apt_packages.sh

./bin/install_flatpaks.sh

sudo ./bin/configure_zsh.sh

./bin/install_oh_my_zsh.sh

sudo ./bin/backup_dot_files.sh

sudo ./bin/install_dots.sh

./bin/install_zsh_autosuggestions.sh

./bin/install_zsh_syntax_highlighting.sh

./bin/add_user_to_docker_group.sh

./bin/install_jetbrains_toolbox.sh

echo "Changing default shell to be zsh..."
chsh -s $(which zsh)

echo "Reloading our ~/.zshrc"
zsh -c "source ~/.zshrc"

./bin/install_vim_plug.sh

./bin/install_vim_plug_plugins.sh

echo "Installation of toolbox was potentially success!\nLogout and log back in, then run again to be sure. This is so ZSH will be your default shell and will source the ~/.zshrc file.";
