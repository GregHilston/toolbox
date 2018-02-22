

install: install_deps install_dots install_submodules install_vim_plugins

install_deps:
	./install/install_deps.sh

install_dots: backup
	./install/install_dots.sh

backup:
	./install/backup.sh

install_bin:
	./install/install_bin.sh

install_submodules:
	git submodule init; \
	git submodule update;

install_vim_plugins:
	vim +PlugInstall +qall

install_ycm:
	~/.vim/bundle/YouCompleteMe/install.sh --gocode-completer; \
	# sudo npm install -g typescript
