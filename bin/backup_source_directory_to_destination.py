import subprocess

from utils import log_locally_and_to_grehg_xyz_slack


def backup_source_directory_to_destination(source_directory_path: str, source_directory_name: str, destination_directory_path: str, destination_directory_name: str):
    """Backups a source directory to a destination either locally or remotely."""
    log_locally_and_to_grehg_xyz_slack(f"Rsync'ing backup from {source_directory_name} ({source_directory_path}) to {destination_directory_name} ({destination_directory_path}) started", "#backup")

    try:
        subprocess.call(["rsync", "-azh", "--progress",  "--update", source_directory_path, destination_directory_path])
        log_locally_and_to_grehg_xyz_slack(f"Rsync'ing backup from {source_directory_name} ({source_directory_path}) to {destination_directory_name} ({destination_directory_path}) finished", "#backup")
    except Exception as e:
        log_locally_and_to_grehg_xyz_slack(f"An exception occurred when Rsyncing backup to {destination_directory_name}. The exception was {str(e)}", "#backup")
