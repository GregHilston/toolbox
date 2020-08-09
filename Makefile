install: helper_ensure_no_sudo install_oh_my_zsh install_dots install_zsh_autosuggestions install_vim_plugins success_message

helper_ensure_no_sudo:
	@echo "Ensuring this was not run with sudo..."
	./install/helper_ensure_no_sudo.sh

backup:
	@echo "Backing up dot files..."
	./install/backup.sh

install_oh_my_zsh:
	@echo "Install oh my zsh..."
	./install/install_oh_my_zsh.sh

install_dots: backup
	@echo "Install dot files..."
	./install/install_dots.sh

source_zshrc:
	@echo "Sourcing zshrc"
	./install/helper_source_zshrc.sh

install_submodules:
	@echo "Installing submodule..."
	./install/install_submodules.sh

install_apt_packages:
	@echo "Installing apt packages..."
	./install/install_apt_packages.sh

install_snap_packages:
	@echo "Installing snap packages..."
	./install/install_snap_packages.sh

install_deb_packages:
	@echo "Installing deb packages..."
	./install/install_deb_packages.sh

install_homebrew:
	@echo "Installing homebrew..."
	./install/install_homebrew.sh

install_homebrew_packages:
	@echo "Installing homebrew packages..."
	./install/install_homebrew_packages.sh

install_pip_packages:
	@echo "Installing pip packages..."
	./install/install_pip_packages.sh

install_zsh:
	@echo "Installing zsh..."
	./install/zsh.sh

install_zsh_as_default:
	# Not needed anymore as oh-my-zsh installation does this
	@echo "Instaling zsh as default shell..."
	./install/install_zsh_as_default.sh

install_zsh_autosuggestions:
	@echo "Installing ZSH auto suggestionse..."
	./install/install_zsh_autosuggestions.sh

install_vim_plugins:
	@echo "Installing vim plugins..."
	vim +PlugInstall +qall

join_zero_tier:
	@echo "Installing well really joining zero tier network"
	./install/install_zero_tier_join_network.sh

success_message:
	@echo "Makefile running was a potentially success!\nLogout and log back in, then run again to be sure. This is so ZSH will be your default shell and will source the ~/.zshrc file, also so snapd's path is setup. Also, don't forget this Makefile has many optional commands!";

# Below are optional packages and not run by default

docker_debian:
	@echo "Installing Docker on debian system..."
	./install/install_docker_debian.sh

docker_arm:
	@echo "Installing Docker on arm system..."
	./install/install_docker_rpi.sh

install_python37:
	@echo "Installing python 3.7..."
	./install/install_python_37.sh

sqlalchemy_dependencies: python37
	@echo "Installing SQL Alchemy dependencies..."
	./install/install_sqlalchemy_dependencies.sh

email_on_boot_with_internet:
	@echo "Installing email on boot with internet..."
	./install/install_email_on_boot_with_internet.sh
	@echo "Don't forget to put gmail_password.conf.personal file in ../secrets"

mount_samba:
	@echo "Installing samba..."
	./install/install_samba.sh
