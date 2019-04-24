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
	# Need to install the zsh-autosuggestions ourselves, no longer shipped
	# used https://gist.github.com/dogrocker/1efb8fd9427779c827058f873b94df95
	# and http://www.geekmind.net/2011/08/how-to-reload-your-zshrc.html
	git clone https://github.com/zsh-users/zsh-autosuggestions.git $ZSH_CUSTOM/plugins/zsh-autosuggestions
	source ~/.zshrc