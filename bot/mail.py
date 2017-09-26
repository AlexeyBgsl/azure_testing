import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging

class GMailer():
    def __init__(self, sender_gmail, pwd, src=None):
        self.sender = sender_gmail
        self.pwd = pwd
        self.src = src if src else sender_gmail

    def send(self, dest, subj, body):
        msg = MIMEMultipart()
        msg['From'] = self.src
        msg['To'] = dest
        msg['Subject'] = subj
        msg.attach(MIMEText(body, 'plain'))
        try:
            server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
            server.ehlo()
            server.login(self.sender, self.pwd)
            server.sendmail(self.src, dest, msg.as_string())
            server.close()
            logging.info("Email sent (to: %s, subj: %s)",
                         dest, subj)
            return True
        except:
            logging.warning("Email sending failed (to: %s, subj: %s)",
                            dest, subj)
            return False
