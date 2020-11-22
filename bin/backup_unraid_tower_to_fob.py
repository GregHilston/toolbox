import subprocess

from utils import send_message_to_grehg_xyz_slack


send_message_to_grehg_xyz_slack("#backup", "Rsyncing backup to Fob started")

try:
    subprocess.call(["rsync", "-azh", "/mnt/user/backup", "pi@fob:/media/hdd/backup/"])
except Exception as e:
    send_message_to_grehg_xyz_slack("#backup", f"An exception occurred when trying to Rsync our backup to remote Fob. The exception was {str(e)}")

send_message_to_grehg_xyz_slack("#backup", "Rsyncing backup to Fob ended")
