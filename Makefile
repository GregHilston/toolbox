.DEFAULT_GOAL := help
.PHONY: help
help: ## This help.
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: helper_ensure_no_sudo install_bare_bones install_essentials install_zsh install_oh_my_zsh install_dots install_zsh_autosuggestions install_vim_plug install_vim_plugins success_message

helper_ensure_no_sudo: ## Ensures this script was not ran by sudo. A helper function.
	@echo "Ensuring this was not run with sudo..."
	./install/helper_ensure_no_sudo.sh

install_bare_bones: ## Installs content not usually available on barebone systems such as Alpine Linux.
	@echo "Installing bare minimum..."
	sudo ./install/install_essential_on_bare_bones.sh

install_essentials: ## Installs only the essentials.
	@echo "Installing essentials..."
	sudo ./install/install_essentials.sh

install_use_vim_as_tool: ## Makes Git use Vim as the default tool to edit files, opposed to Nano.
	@echo "Using Vim as tool..."
	sudo ./install/install_vim_as_git_tool.sh

backup: ## Backs up dot files. Ensures we don't replace anything by accident.
	@echo "Backing up dot files..."
	./install/backup.sh

install_oh_my_zsh: ## Installs oh my zsh.
	@echo "Installing oh my zsh..."
	./install/install_oh_my_zsh.sh

install_dots: backup ## Installs my personal dot files.
	@echo "Installing dot files..."
	./install/install_dots.sh

source_zshrc: ## Reloads the zshrc file.
	@echo "Sourcing zshrc"
	./install/helper_source_zshrc.sh

install_submodules:
	@echo "Installing submodule..."
	./install/install_submodules.sh

install_apt_packages: ## Installs my favorite apt packages.
	@echo "Installing apt packages..."
	./install/install_apt_packages.sh

install_snap_packages: ## Installs my favorite snap packages.
	@echo "Installing snap packages..."
	./install/install_snap_packages.sh

install_deb_packages: ## Installs my favorite deb packages.
	@echo "Installing deb packages..."
	./install/install_deb_packages.sh

install_homebrew: ## Installs homebrew, that package manager.
	@echo "Installing homebrew..."
	./install/install_homebrew.sh

install_homebrew_packages: ## Installs my favorite homebrew packages. 
	@echo "Installing homebrew packages..."
	./install/install_homebrew_packages.sh

install_pip_packages: ## Installs my favorite pip packages.
	@echo "Installing pip packages..."
	./install/install_pip_packages.sh

install_zsh:
	@echo "Installing zsh..."
	./install/install_zsh.sh

configure_git:
	@echo "Configuring Git..."
	./install/configure_git.sh

install_zsh_as_default:
	# Not needed anymore as oh-my-zsh installation does this
	@echo "Instaling zsh as default shell..."
	./install/install_zsh_as_default.sh

install_zsh_autosuggestions:
	@echo "Installing ZSH auto suggestionse..."
	./install/install_zsh_autosuggestions.sh
	# TODO investigate why may get output [oh-my-zsh] plugin 'zsh-syntax-highlighting' not found

install_vim_plug:
	@echo "Installing vim plug"
	./install/install_vim_plug.sh

install_vim_plugins:
	@echo "Installing vim plugins..."
	# TODO might need to source ~/.zshrc before running this
	vim +PlugInstall +qall

join_zero_tier:
	@echo "Installing well really joining zero tier network"
	./install/install_zero_tier_join_network.sh

success_message:
	@echo "Makefile running was potentially success!\nLogout and log back in, then run again to be sure. This is so ZSH will be your default shell and will source the ~/.zshrc file, also so snapd's path is setup. Also, don't forget this Makefile has many optional commands!";

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
