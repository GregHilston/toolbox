install: install_packages install_submodules install_dots install_zsh_as_default install_zsh_autocomplete success_message

backup:
	@echo "Backing up dot files..."
	./install/backup.sh

install_dots: backup
	@echo "Install dot files..."
	./install/install_dots.sh

install_submodules:
	@echo "Installing submodule..."
	./install/install_submodules.sh

install_packages:
	@echo "Installing apt packages..."
	./install/install_apt_packages.sh

install_zsh_as_default:
	@echo "Instaling zsh as default shell..."
	sudo ./install/install_zsh_as_default.sh

install_zsh_autocomplete:
	@echo "Installing ZSH auto complete..."
	./install/install_zsh_autocomplete.sh

success_message:
	@echo "Makefile running was a success!\nLogout and log back in for ZSH to be your default shell or run ZSH right now and future logins should work just fine";

# Below are optional packages and not run by default

docker_debian:
	@echo "Installing Docker on debian system..."
	./install/install_docker_debian.sh

docker_arm:
	@echo "Installing Docker on arm system..."
	./install/install_docker_rpi.sh

python37:
	@echo "Installing python 3.7..."
	./install/install_python_37.sh

sqlalchemy_dependencies: python37
	@echo "Installing SQL Alchemy dependencies..."
	./install/install_sqlalchemy_dependencies.sh

email_on_boot_with_internet:
	@echo "Installing email on boot with internet..."
	./install/install_email_on_boot_with_internet.sh

mount_samba:
	@echo "Installing samba..."
	./install/install_samba.sh