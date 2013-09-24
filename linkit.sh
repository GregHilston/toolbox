mkdir .old
mv ~/.vimrc     .old/
mv ~/.vim       .old/
mv ~/.tmux.conf .old/
mv ~/.zshrc     .old/
mv ~/.bashrc    .old/

ln -s .vimrc     ~/.vimrc
ln -s .vim       ~/.vim
ln -s .tmux.conf ~/.tmux.conf
ln -s .zshrc     ~/.zshrc
ln -s .bashrc    ~/.bashrc
