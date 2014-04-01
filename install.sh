#!/bin/bash

DIR=$(pwd)
FILES=( bashrc zshrc tmux.conf vimrc)

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

# Install pathogen
if [ -d vim/autoload/pathogen.vim ]; then
   echo "Pathogen already installed"
else
   mkdir -p ~/.vim/autoload ~/.vim/bundle; \
   curl -so ~/.vim/autoload/pathogen.vim \
   https://raw.github.com/tpope/vim-pathogen/master/autoload/pathogen.vim
   echo "Pathogen installed OK"
fi

# Install syntastic
if [ -d vim/bundle/syntastic ]; then
    echo "Syntastic already installed"
else
    cd ~/.vim/bundle
    git clone https://github.com/scrooloose/syntastic.git
    cd DIR
    echo "Syntastic installed OK"
fi

# Install nerdtree
if [ -d vim/bundle/nerdtree ]; then
    echo "Nerdtree alreadt installed"
else
    cd ~/.vim/bundle
    git clone https://github.com/scrooloose/nerdtree.git
    cd DIR
    echo "Nerdtree installed OK"
fi
