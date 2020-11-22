import subprocess

from send_message_to_grehg_xyz_slack import send_message_to_grehg_xyz_slack


send_message_to_grehg_xyz_slack("#backup", "Rsyncing backup to unassinged drive started")

try:
    subprocess.call(["rsync", "-azh", "/mnt/user/backup", "/mnt/disks/mothership"])
except Exception as e:
    send_message_to_grehg_xyz_slack("#backup", f"An exception occurred when trying to Rsync our backup to unassigned drive. The exception was {str(e)}")

send_message_to_grehg_xyz_slack("#backup", "Rsyncing backup to unassigned drive ended")
