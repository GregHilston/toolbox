#!/usr/bin/env python

import os
import shutil

# Define needed paths and files to install
home = os.environ['HOME']
repo_root = os.path.dirname(os.path.realpath(__file__))
dotfile_path = os.path.join(repo_root, 'dots')
lib_path = os.path.join(repo_root, 'lib')
backup = os.path.join(repo_root, 'backup')
install = os.listdir(dotfile_path) + os.listdir(lib_path)


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
        print(" > {}".format(source))
        if os.path.exists(source):
            shutil.move(source, dest)
            print("   {} -> {}".format(dest, source))
        elif os.path.islink(source):
            os.unlink(source)
            print("   Removing link")

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
    print "Installing {}\n".format(install)
    backup_old_files(home, backup, install)
    create_symlinks(home, dotfile_path, install)
