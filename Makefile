.DEFAULT_GOAL := help
.PHONY: help
help: ## This help.
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: install_ensure_no_sudo install_bare_bones install_essentials install_zsh install_oh_my_zsh install_dots install_zsh_autosuggestions install_vim_plug install_vim_plugins success_message ## Installs and configures our whole system.

backup:
	./install/backup_dot_files.sh

helper_ensure_no_sudo: ## Ensures this script was not ran by sudo. A helper function.
	@echo "Ensuring this was not run with sudo..."
	./install/helper_ensure_no_sudo.sh

install_bare_bones: ## Installs content not usually available on barebone systems such as Alpine Linux or a fresh Ubuntu container.
	@echo "Installing bare minimum..."
	sudo ./install/install_essential_on_bare_bones.sh

install_essentials: ## Installs only the essentials.
	@echo "Installing essentials..."
	sudo ./install/install_essentials.sh

install_oh_my_zsh: ## Installs oh my zsh.
	@echo "Installing oh my zsh..."
	./install/install_oh_my_zsh.sh

install_dots: backup ## Installs my personal dot files.
	@echo "Installing dot files..."
	./install/install_dots.sh

install_zsh:
	@echo "Installing zsh..."
	./install/install_zsh.sh

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

success_message:
	@echo "Makefile running was potentially success!\nLogout and log back in, then run again to be sure. This is so ZSH will be your default shell and will source the ~/.zshrc file.";
