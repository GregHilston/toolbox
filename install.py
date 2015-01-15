#!/usr/bin/env python

import os
import shutil

files_to_install = [
    'bashrc',
    'tmux.conf',
    'vim',
    'vimrc',
    'zshrc',
    'oh-my-zsh'
]

# Define needed paths and files to install
home = os.environ['HOME']
dotfile_path = os.path.dirname(os.path.realpath(__file__))
backup = os.path.join(dotfile_path, "backup")
print "Installing {}\n".format(files_to_install)


def backup_old_files(home, backup, sources):
    print("Backing up files")

    if os.path.exists(backup):
        print(" > Removing old backup dir")
        shutil.rmtree(backup, ignore_errors=True)

    if not os.path.exists(backup):
        print(" > Creating new backup dir")
        os.makedirs(backup)

    for source in sources:
        dest = os.path.join(backup, source)
        source = os.path.join(home, '.' + source)
        if os.path.exists(source):
            shutil.move(source, dest)
            print(" > {} -> {}".format(dest, source))

    print("Done\n")


def create_symlinks(home, dotfile_path, sources):
    print("Creating symlink")

    for source in sources:
        dest = os.path.join(home, '.' + source)
        source = os.path.join(dotfile_path, source)
        if not os.path.exists(dest):
            os.symlink(source, dest)
            print(" > {} -> {}".format(dest, source))

    print("Done\n")


if __name__ == '__main__':
    backup_old_files(home, backup, files_to_install)
    create_symlinks(home, dotfile_path, files_to_install)
