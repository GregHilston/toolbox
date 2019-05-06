#!/usr/bin/env python

import subprocess
import smtplib
from email.mime.text import MIMEText
import datetime

to = 'Grehgh@gmail.com'
gmail_user = 'grehgpi@gmail.com'
gmail_password = ''

with open ("../secrets/gmail_password.conf.personal", "r") as myfile:
    gmail_password=myfile.read().replace('\n', '')

smtpserver = smtplib.SMTP('smtp.gmail.com',587)
smtpserver.ehlo()
smtpserver.starttls()
smtpserver.ehlo
smtpserver.login(gmail_user, gmail_password)
today = datetime.date.today()
arg='ip route list'
p=subprocess.Popen(arg,shell=True,stdout=subprocess.PIPE)
data = p.communicate()
split_data = data[0].split()
print(split_data)
ipaddr = split_data[split_data.index('src')+1]
my_ip = 'Your ip is %s' % ipaddr
msg = MIMEText(my_ip)
msg['Subject'] = 'IP For RaspberryPi'
msg['From'] = gmail_user
msg['To'] = to
smtpserver.sendmail(gmail_user, [to], msg.as_string())
smtpserver.quit()