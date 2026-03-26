# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "loguru",
# ]
# ///
"""Email this device's IP addresses and hostname to a given address"""

import argparse
import os
import smtplib
import socket
import subprocess
import sys
from email.mime.text import MIMEText

from loguru import logger


def get_ipv4_address() -> str:
    """Look up this device's IPv4 address."""
    result = subprocess.run(
        "ifconfig | grep -Eo 'inet (addr:)?([0-9]*\\.){3}[0-9]*' | grep -Eo '([0-9]*\\.){3}[0-9]*' | grep -v '127.0.0.1'",
        shell=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def get_ipv6_address() -> str:
    """Look up this device's IPv6 address."""
    result = subprocess.run(
        "/sbin/ip -6 addr | grep inet6 | awk -F '[ \\t]+|/' '{print $3}' | grep -v ^::1 | grep -v ^fe80",
        shell=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def get_host_name() -> str:
    """Look up this device's hostname."""
    return socket.gethostname()


def send_email(
    from_email_address: str,
    to_email_address: str,
    subject: str,
    body: str,
    from_email_address_password: str | None = None,
):
    if not from_email_address_password:
        key = "FROM_EMAIL_ADDRESS_PASSWORD"
        logger.warning(f"Password not provided, falling back to ${key}")
        from_email_address_password = os.environ.get(key)

    if not from_email_address_password:
        password_file = os.path.join(
            os.path.dirname(sys.argv[0]),
            "secrets",
            "gmail_password.conf.personal",
        )
        logger.warning(f"Env var not set, falling back to file: {password_file}")
        with open(password_file) as f:
            from_email_address_password = f.read().strip()

    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.ehlo()
    server.starttls()
    server.ehlo()
    server.login(from_email_address, from_email_address_password)

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = from_email_address
    msg["To"] = to_email_address
    server.sendmail(from_email_address, [to_email_address], msg.as_string())
    server.quit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Email this device's IP info")
    parser.add_argument("--from_email_address", "-f", type=str, required=True)
    parser.add_argument("--to_email_address", "-t", type=str, required=True)
    args = parser.parse_args()

    hostname = get_host_name()
    body = (
        f"IPv4 Address = {get_ipv4_address()}\n"
        f"IPv6 Address = {get_ipv6_address()}\n"
        f"Hostname = {hostname}\n"
    )
    subject = f"{hostname} powered on with internet"

    send_email(args.from_email_address, args.to_email_address, subject, body)
