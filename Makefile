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
	@echo "Installing apt packages..."
	./install/install_apt_packages.sh

install_zsh_as_default:
	@echo "Instaling zsh as default shell..."
	sudo ./install/install_zsh_as_default.sh

install_zsh_autocomplete:
	@echo "Installing ZSH auto complete"
	./install/install_zsh_autocomplete.sh

success_message:
	@echo "Makefile running was a success!\nLogout and log back in for ZSH to be your default shell or run ZSH right now and future logins should work just fine";

# Below are optional packages

docker_debian:
	@echo "Installing Docker on debian system..."
	./install/install_docker_debian.sh

docker_arm:
	@echo "Installing Docker on arm system..."
	./install/install_docker_rpi.sh

python37:
	# From https://linuxize.com/post/how-to-install-python-3-7-on-ubuntu-18-04/

	# Start by updating the packages list and installing the prerequisites:
	apt update \
	apt install software-properties-common -y \

	# Next, add the deadsnakes PPA to your sources list:
	add-apt-repository ppa:deadsnakes/ppa -y \

	# Once the repository is enabled, install Python 3.7 and venv:
	apt install python3.7 python3.7-venv -y \

	# At this point, Python 3.7 is installed on your Ubuntu system and ready to be used.
	@echo "Python3.7 should be installed, use by running '\$ python3.7'

sqlalchemy_dependencies: python37
	# Installing the dev for python 37 and the client,
	apt install python3.7-dev -y default-libmysqlclient-dev -y \

email_on_internet_access:


mount_samba:
	@echo "Installing samba"

	./install/install_samba.sh