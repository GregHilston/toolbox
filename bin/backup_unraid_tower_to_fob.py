from backup_source_directory_to_destination import backup_source_directory_to_destination 


backup_source_directory_to_destination(
    source_directory_path="/mnt/user/backup/", # trailing slash means contents of backup will be written to backup-from-unraid
    source_directory_name="unraid backup share",
    destination_directory_path="pi@fob:/mnt/mothership/backup-from-unraid/",
    destination_directory_name="Fob external hard drive"
)
