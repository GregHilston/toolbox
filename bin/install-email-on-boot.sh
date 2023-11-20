#!/bin/bash
set -euo pipefail
IFS=$'\n\t'

# Backup any original rc.local that may exist
SCRIPT_HOME=$(cd "$(dirname $0)" && pwd)
TOOLBOX_HOME=$(echo $SCRIPT_HOME | rev | cut -d/ -f2- | rev)

BACKUP_DIR=$TOOLBOX_HOME/backup
THIS_BACKUP=$BACKUP_DIR/backup-$(rc.local date +%F-%T)

if [ ! -d $BACKUP_DIR ]; then
  echo Create $BACKUP_DIR
  mkdir "$BACKUP_DIR"
fi

echo Backing up current configuration into [$THIS_BACKUP]

mkdir "$THIS_BACKUP"

result="Backed up: "
for backup_file in "${BACKUPS[@]}"; do
  if [ -f "/etc/rc.local" ]; then
    cp "/etc/rc.local" "$THIS_BACKUP/$backup_file"
    $result="$result $backup_file"
  fi
done

echo $result

# Link in new rc.local
SCRIPT_HOME=$(cd "$(dirname $0)" && pwd)
TOOLBOX_HOME=$(echo $SCRIPT_HOME | rev | cut -d/ -f2- | rev)

printf "Installing rc.local (email IP address on boot)... "
rm -rf /etc/rc.local
ln -s "$HOME/.rc.local" "/etc/rc.local"
echo "Done"
