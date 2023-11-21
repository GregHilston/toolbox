import os
import socket
import sys
import subprocess
import typing
import json

import requests
import smtplib
from email.mime.text import MIMEText
from loguru import logger

from typing import Optional

def send_pushover_notification(message: str='Hello World', pushover_user_key: Optional[str] = None, pushover_work_api_key: Optional[str] = None):
    """Sends a notification to Pushover

    Args:
        message: Message to send in Pushover notification

    Returns:
        HTTP response
    """
    if not pushover_user_key:
        pushover_user_key_environment_variable_key = 'PUSHOVER_USER_KEY'
        logger.warning(f'pushover_user_key not provided, falling back to environment variable "${pushover_user_key_environment_variable_key}"')
        pushover_user_key = os.environ[pushover_user_key_environment_variable_key]

    if not pushover_work_api_key:
        pushover_work_api_key_environment_variable_key = 'PUSHOVER_WORK_API_KEY'
        logger.warning(f'pushover_work_api_key not provided, falling back to environment variable "{pushover_work_api_key_environment_variable_key}"')
        pushover_work_api_key = os.environ[pushover_work_api_key_environment_variable_key]

    response = requests.post(
            'https://api.pushover.net/1/messages.json',
        data = {
            'user': pushover_user_key,
            'token': pushover_work_api_key,
            'message': message
        }
    )
    return response

def send_email(from_email_address: str, to_email_address: str, subject: str, body: str, from_email_address_password: typing.Optional[str] = None):
    """Sends an email address from our GrehgPi email address.

    Args:
        from_email_address: Email address to send the email from
        from_email_address_password: Password for from email address
        to_email_address: Email address to send the email to
        subject: Subject of the email
        body: Body of the email
    """
    # Gets path based on where this script is located and not from where we
    # execute it from
    secrets_directory_relative_to_this_folder = os.path.join(os.path.dirname(sys.argv[0]), 'secrets')

    if not from_email_address_password:
        from_email_address_password_environment_variable_key = 'FROM_EMAIL_ADDRESS_PASSWORD'
        logger.warning(f'from_email_address_password not provided, falling back to environment variable "${from_email_address_password_environment_variable_key}"')
        from_email_address_password = os.environ[from_email_address_password_environment_variable_key]

        if not from_email_address_password:
            from_email_address_password_file = os.path.join(secrets_directory_relative_to_this_folder, 'gmail_password.conf.personal')
            logger.warning(f'environment variable "{from_email_address_password_environment_variable_key}" not provided, falling back file based password by looking at "{from_email_address_password_file}"')
            with open (from_email_address_password_file, 'r') as myfile:
                from_email_address_password=myfile.read().replace('\n', '')

    smtpserver = smtplib.SMTP('smtp.gmail.com', 587)
    smtpserver.ehlo()
    smtpserver.starttls()
    smtpserver.ehlo

    smtpserver.login(from_email_address, from_email_address_password)

    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = from_email_address
    msg['To'] = to_email_address
    smtpserver.sendmail(from_email_address, [to_email_address], msg.as_string())
    smtpserver.quit()

def get_ipv4_address() -> str:
    """Looks up this device's ipv4 address

    Returns:
        ipv4 address
    """
    sh_command = "ifconfig | grep -Eo 'inet (addr:)?([0-9]*\.){3}[0-9]*' | grep -Eo '([0-9]*\.){3}[0-9]*' | grep -v '127.0.0.1'"

    ps = subprocess.Popen(sh_command,shell=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    byte_output = ps.communicate()[0]
    string_output = byte_output.decode("utf-8")

    return string_output

def get_ipv6_address() -> str:
    """Looks up this device's ipv4 address

    Returns:
        ipv4 address
    """
    sh_command = "/sbin/ip -6 addr | grep inet6 | awk -F '[ \t]+|/' '{print $3}' | grep -v ^::1 | grep -v ^fe80"

    ps = subprocess.Popen(sh_command,shell=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    byte_output = ps.communicate()[0]
    string_output = byte_output.decode("utf-8")

    return string_output

def get_host_name() -> str:
    """Looks up this device's hostname"""
    return socket.gethostname()
