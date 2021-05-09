import subprocess

from utils import log_locally_and_to_grehg_xyz_slack


def backup_source_directory_to_destination(source_directory_path: str, source_directory_name: str, destination_directory_path: str, destination_directory_name: str):
    """Backups a source directory to a destination either locally or remotely."""
    log_locally_and_to_grehg_xyz_slack("#backup", f"Rsync'ing backup to {destination_directory_name} started")

    try:
        subprocess.call(["rsync", "-azh", "--progress",  "--update", source_directory_path, destination_directory_path])
        log_locally_and_to_grehg_xyz_slack("#backup", f"Rsyncing backup to {destination_directory_name} finished successfully")
    except Exception as e:
        log_locally_and_to_grehg_xyz_slack("#backup", f"An exception occurred when trying to Rsync {source_directory_name} to {destination_directory_name}. The exception was {str(e)}")