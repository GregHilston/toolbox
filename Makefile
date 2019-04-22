install: install_dots install_submodules install_packages

install_dots: backup
	./install/install_dots.sh

install_submodules:
	git submodule init; \
	git submodule update;

install_packages:
	apt-get install tmux vim -y

backup:
	./install/backup.sh