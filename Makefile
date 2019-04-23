install: install_dots install_submodules install_packages

backup:
	./install/backup.sh

install_dots:
	backup
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
    && git clone https://github.com/GregHilston/toolbox.gitapt-get