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
	htop \
	zsh

install_zsh_as_default:
	@echo "Instaling zsh as default shell..."
	sudo ./install/install_zsh_as_default.sh

install_zsh_autocomplete:
	@echo "Installing ZSH auto complete"
	./install/install_zsh_autocomplete.sh

success_message:
	@echo "Makefile running was a success!\nLogout and log back in for ZSH to be your default shell or run ZSH right now and future logins should work just fine";

# Below are optional packages

docker:
	# From https://www.digitalocean.com/community/tutorials/how-to-install-and-use-docker-on-ubuntu-18-04

	# First, update your existing list of packages:
	apt update \

	# Next, install a few prerequisite packages which let apt use packages over HTTPS:
	apt install apt-transport-https ca-certificates curl software-properties-common -y \

	# Then add the GPG key for the official Docker repository to your system:
	curl -fsSL https://download.docker.com/linux/ubuntu/gpg | apt-key add - \

	# Add the Docker repository to APT sources:
	add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu bionic stable" \

	# Next, update the package database with the Docker packages from the newly added repo:
	apt update \

	# Make sure you are about to install from the Docker repo instead of the default Ubuntu repo:
	apt-cache policy docker-ce \

	# You'll see output like this, although the version number for Docker may be different:
	# docker-ce:
  	# Installed: (none)
  	# Candidate: 18.03.1~ce~3-0~ubuntu
  	# Version table:
		# 18.03.1~ce~3-0~ubuntu 500
		# 500 https://download.docker.com/linux/ubuntu bionic/stable amd64 Packages

	# Notice that docker-ce is not installed, but the candidate for installation is from the Docker repository for Ubuntu 18.04 (bionic). 

	# Finally, install Docker:
	apt install docker-ce systemd -y \

	@echo "Docker should now be installed, the daemon started, and the process enabled to start on boot. Check that it's running by running '\$sudo systemctl status docker'"

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

pymysql: python37
	# Installing the dev for python 37 and the client,
	apt install python3.7-dev -y default-libmysqlclient-dev -y \