#!/usr/bin/env python3.7

import subprocess
import smtplib
from email.mime.text import MIMEText
import datetime
import sys, os
import socket

to = 'Grehgh@gmail.com'
gmail_user = 'grehgpi@gmail.com'
gmail_password = ''

def get_ipv4_address():
    sh_command = "ifconfig | grep -Eo 'inet (addr:)?([0-9]*\.){3}[0-9]*' | grep -Eo '([0-9]*\.){3}[0-9]*' | grep -v '127.0.0.1'"

    ps = subprocess.Popen(sh_command,shell=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    byte_output = ps.communicate()[0]
    string_output = byte_output.decode("utf-8")

    return string_output

def get_ipv6_address():
    sh_command = "/sbin/ip -6 addr | grep inet6 | awk -F '[ \t]+|/' '{print $3}' | grep -v ^::1 | grep -v ^fe80"

    ps = subprocess.Popen(sh_command,shell=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    byte_output = ps.communicate()[0]
    string_output = byte_output.decode("utf-8")

    return string_output

def get_host_name():
    return socket.gethostname()

# so we can get path based on where this script is located
# and not from where we execute it from
with open (f"{os.path.dirname(sys.argv[0])}/../secrets/gmail_password.conf.personal", "r") as myfile:
    gmail_password=myfile.read().replace('\n', '')

smtpserver = smtplib.SMTP('smtp.gmail.com',587)
smtpserver.ehlo()
smtpserver.starttls()
smtpserver.ehlo
smtpserver.login(gmail_user, gmail_password)

body = ''
body += f"IPV4 Address = {get_ipv4_address()}"
body += f"IPV6 Address = {get_ipv6_address()}"
body +=  f"hostname = {get_host_name()}"

msg = MIMEText(body)
msg['Subject'] = f"{get_host_name()} powered on with internet"
msg['From'] = gmail_user
msg['To'] = to
smtpserver.sendmail(gmail_user, [to], msg.as_string())
smtpserver.quit()