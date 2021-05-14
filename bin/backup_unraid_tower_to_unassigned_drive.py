from backup_source_directory_to_destination import backup_source_directory_to_destination 


backup_source_directory_to_destination(
    source_directory_path="/mnt/user/backup", # lack of traling slash means the backup directory will be copied to mothership
    source_directory_name="unraid backup share",
    destination_directory_path="/mnt/disks/mothership",
    destination_directory_name="Unraid external hard drive"
)
