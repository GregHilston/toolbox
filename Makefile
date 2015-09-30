

install: install_dots install_submodules install_vundle install_ycm

install_dots: backup
	./install/install_dots.sh

backup:
	./install/backup.sh

install_bin:
	./install/install_bin.sh

install_submodules:
	git submodule init; \
	git fetch

install_vundle:
	vim +PluginInstall +qall

install_ycm:
	~/.vim/bundle/YouCompleteMe/install.py --gocode-completer; \
	sudo npm install -g typescript
