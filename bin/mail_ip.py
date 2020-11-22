#!/usr/bin/env python3.7

import subprocess
import socket

from utils import send_email


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

to_email_address = 'Grehgh@gmail.com'

body = ""
body += f"IPV4 Address = {get_ipv4_address()}"
body += f"IPV6 Address = {get_ipv6_address()}"
body +=  f"hostname = {get_host_name()}"

subject = f"{get_host_name()} powered on with internet"

send_email(to_email_address, subject, body)
