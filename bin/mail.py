import os
import sys

import smtplib
from email.mime.text import MIMEText


def send_email(to_email_address: str, subject: str, body: str):
    """Sends an email address from our GrehgPi email address."""
    # so we can get path based on where this script is located
    # and not from where we execute it from
    secrets_directory_relative_to_this_folder = os.path.join(os.path.dirname(sys.argv[0]), "..", "secrets")

    from_email_address="GrehgPi@gmail.com"

    with open (os.path.join(secrets_directory_relative_to_this_folder, "gmail_password.conf.personal"), "r") as myfile:
        gmail_password=myfile.read().replace("\n", "")

    smtpserver = smtplib.SMTP("smtp.gmail.com",587)
    smtpserver.ehlo()
    smtpserver.starttls()
    smtpserver.ehlo
    
    smtpserver.login(from_email_address, gmail_password)

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = "grehgpi@gmail.com"
    msg["To"] = to_email_address
    smtpserver.sendmail(from_email_address, [to_email_address], msg.as_string())
    smtpserver.quit()
