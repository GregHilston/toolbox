install: install_dots install_submodules

install_dots: backup
	./install/install_dots.sh

backup:
	./install/backup.sh

install_submodules:
	git submodule init; \
	git submodule update;