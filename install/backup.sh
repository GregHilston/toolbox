#!/usr/bin/env bash
set -e

SCRIPT_HOME=$(cd "$(dirname $0)" && pwd)
TOOLBOX_HOME=$(echo $SCRIPT_HOME | rev | cut -d/ -f2- | rev)

BACKUP_DIR=$TOOLBOX_HOME/backup
THIS_BACKUP=$BACKUP_DIR/backup-$(date +%F-%T)
BACKUPS=(bashrc gitignore tmux.conf vimrc zshrc env vim)

if [ ! -d $BACKUP_DIR ]; then
  echo Create $BACKUP_DIR
  mkdir "$BACKUP_DIR"
fi

echo Backing up current configuration into [$THIS_BACKUP]
mkdir "$THIS_BACKUP"

result="Backed up: "
for backup_file in "${BACKUPS[@]}"; do
  if [ -f "~/.$backup_file" ]; then
    cp "~/.$backup_file" "$THIS_BACKUP/$backup_file"
    $result="$result $backup_file"
  fi
done

echo $result
