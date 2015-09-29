install: install_dots install_bin

install_dots: backup
	./install/install_dots.sh

install_bin:
	./install/install_bin.sh

backup:
	./install/backup.sh
