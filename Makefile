install: install_packages install_submodules install_dots  install_zsh_autocomplete

backup:
	./install/backup.sh

install_dots: backup
	./install/install_dots.sh

install_submodules:
	git submodule init; \
	git submodule update;

install_packages:
	apt-get update \
    && apt-get install -y \
    git \
    build-essential \
    tmux \
    vim \
	zsh

install_zsh_autocomplete:
	./install/install_zsh_autocomplete.sh