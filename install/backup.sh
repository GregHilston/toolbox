#!/usr/bin/env bash
SCRIPT_HOME=$(cd "$(dirname $0)" && pwd)
TOOLBOX_HOME=$(echo $SCRIPT_HOME | rev | cut -d/ -f2- | rev)

BACKUP_DIR=$TOOLBOX_HOME/backup
THIS_BACK_UP=$BACKUP_DIR/backup-$(date +%F-%T)
FILES_TO_BACKUP=(bashrc gitignore tmux.conf vimrc zshrc)
DIRS_TO_BACKUP=(env oh-my-zsh vim zsh)

if [ ! -d $BACKUP_DIR ]; then
  echo Create $BACKUP_DIR
  mkdir $BACKUP_DIR
fi

echo Backing up current configuration into [$THIS_BACK_UP]
mkdir $THIS_BACKUP
