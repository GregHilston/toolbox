install: helper_ensure_no_sudo install_apt_packages install_pip_packages install_submodules install_dots  install_zsh_as_default install_zsh_autocomplete success_message

helper_ensure_no_sudo:
	@echo "Ensuring this was not run with sudo..."
	./install/helper_ensure_no_sudo.sh

backup:
	@echo "Backing up dot files..."
	./install/backup.sh

install_dots: backup
	@echo "Install dot files..."
	./install/install_dots.sh

source_zshrc:
	@echo "Sourcing zshrc"
	./install/helper_source_zshrc.sh

install_submodules:
	@echo "Installing submodule..."
	./install/install_submodules.sh

install_apt_packages:
	@echo "Installing apt packages..."
	./install/install_apt_packages.sh

install_pip_packages:
	@echo "Installing pip packages..."
	./install/install_pip_packages.sh

install_zsh_as_default:
	@echo "Instaling zsh as default shell..."
	./install/install_zsh_as_default.sh

install_zsh_autocomplete:
	@echo "Installing ZSH auto complete..."
	./install/install_zsh_autocomplete.sh

success_message:
	@echo "Makefile running was a potentially success!\nLogout and log back in, then run again to be sure. This is so ZSH will be your default shell and will source the ~/.zshrc file. Also, don't forget this Makefile has many optional commands!";

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
	@echo "Don't forget to put gmail_password.conf.personal file in ../secrets"

mount_samba:
	@echo "Installing samba..."
	./install/install_samba.sh
