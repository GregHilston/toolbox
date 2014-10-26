#!/bin/bash

DIR=$(pwd)
FILES=(bashrc zshrc tmux.conf vimrc)

echo "Creating backups..."

# Create necessary folders
if [ ! -d backup ]; then
    mkdir backup
fi

if [ ! -d backup/tmp ]; then
    mkdir backup/tmp
fi

# Backup and remove old files
for f in "${FILES[@]}"
do
    if [ -f ~/.$f ]; then
        mv ~/.$f backup/tmp/$f
        rm backup/$f
	mv backup/tmp/$f backup/
	echo "$f backup OK"
    elif [ -h ~/.$f ]; then
        rm ~/.$f
	echo "$f removing symlink OK"
    else
        echo "~/.$f does not exist"
    fi
done

if [ -f ~/.vim ]; then
    mv ~/.vim backup/tmp/vim
    rm -r backup/vim
    mv backup/tmp/vim backup/
    echo "vim backup OK"
elif [ -h ~/.vim ]; then
    rm ~/.vim
    echo "vim removing symlink OK"
else
    echo "~/.vim does not exist"
fi

echo "Removing tmp directory..."
rm -r backup/tmp

echo "Done"

# Create symlinks
echo "Creating symlinks..."
for f in "${FILES[@]}"
do
    ln -s $(pwd)/$f ~/.$f
done
ln -s $(pwd)/vim ~/.vim
echo "Done"

# Install Vundle
if [ -d vim/bundle/Vundle.vim ]; then
    git pull vim/bundle/Vundle.vim
    echo "Vundle updated"
else
    git clone https://github.com/gmarik/Vundle.vim.git vim/bundle/Vundle.vim
    echo "Vundle installed OK"
fi
vim +PluginInstall +qall
echo "Installed Vundle plugins"

# Configure YouCompleteMe plugin
git submodule update --init --recursive vim/bundle/YouCompleteMe
./vim/bundle/YouCompleteMe/install.sh

echo "Finished installing"
