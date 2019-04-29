install: install_packages install_submodules install_dots install_zsh_as_default install_zsh_autocomplete success_message

backup:
	@echo "Backing up dot files..."
	./install/backup.sh

install_dots: backup
	@echo "Install dot files..."
	./install/install_dots.sh

install_submodules:
	@echo "Installing submodule..."
	git submodule init; \
	git submodule update;

install_packages:
	@echo "Installing packages..."
	apt-get update \
    && apt-get install -y \
    git \
    build-essential \
    tmux \
    vim \
	zsh

install_zsh_as_default:
	@echo "Instaling zsh as default shell..."
	sudo ./install/install_zsh_as_default.sh

install_zsh_autocomplete:
	@echo "Installing ZSH auto complete"
	./install/install_zsh_autocomplete.sh

success_message:
	@echo "Makefile running was a success!\nLogout and log back in for ZSH to be your default shell or run ZSH right now and future logins should work just fine"
