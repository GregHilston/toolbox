from send_message_to_grehg_xyz_slack import send_message_to_grehg_xyz_slack


send_message_to_grehg_xyz_slack("#backup", "Rsyncing backup to Fob started")


# rsync -azh --progress --password-file=passFile /mnt/user/backup/ pi@fob:/media/hdd/backup/
# sshpass -p $(cat passFile) rsync -azh --progress /mnt/user/backup/ pi@fob:/media/hdd/backup/

send_message_to_grehg_xyz_slack("#backup", "Rsyncing backup to Fob ended")
