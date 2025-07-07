import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.mime.text import MIMEText
from pathlib import Path
from datetime import datetime
import logging
import os

logger = logging.getLogger("fs_logger")

class Mailer:
    def __init__(self, server='172.17.0.126', port=25, sender='Kaustubh.Keny@cogencis.com', recipients=['Kaustubh.Keny@cogencis.com']):
        self.SERVER = server
        self.PORT = port
        self.FROM = sender
        self.RECPTS = recipients or []

    def started(self, program):
        subject = f"{program} — Execution Started"
        body = f"""
        <html>
            <body>
                <p>Hello Team,</p>
                <p>The program <b>{program}</b> has <b>started</b>.</p>
                <p>Regards,<br>Kaustubh</p>
            </body>
        </html>
        """
        msg = self.construct_mail(subject=subject, body_html=body)
        self.send_mail(msg)
        logger.info(f"Program Started Mail Sent: {program}")
    
    def end(self, program, data=None):
        subject = f"{program} — Execution Completed"
        process, failed = data

        completed_amcs = '<br>'.join(process.keys())
        failed_amcs = '<br>'.join(failed.keys())
        body = f"""
        <html>
            <body>
                <p>Hello Team,</p>
                <p>The program <b>{program}</b> has <b>completed</b> execution.</p>
                <table border="1" cellspacing="0" cellpadding="5">
                    <tr><th>AMC's Completed</th><th>AMC's Failed</th></tr>
                    <tr><td>{completed_amcs}</td><td>{failed_amcs}</td></tr>
                </table>
                <p>Regards,<br>Kaustubh</p>
            </body>
        </html>
        """
        msg = self.construct_mail(subject=subject, body_html=body)
        self.send_mail(msg)
        logger.info(f"Program Ended Mail Sent: {program}")


    def construct_mail(self, subject, body_html=None):
        msg = MIMEMultipart()
        msg['From'] = self.FROM
        msg['To'] = ', '.join(self.RECPTS)
        msg['Subject'] = f"{subject} - {datetime.now().strftime('%Y-%m-%d')}"

        body_html = body_html or self.default_body()
        msg.attach(MIMEText(body_html, 'html'))
        return msg

    def default_body(self):
        return """
        <html>
            <body>
                <p>Hello Team,</p>
                <p>The FS JSON DATA parsing completed.</p>
                <p>Regards,<br>Kaustubh</p>
            </body>
        </html>
        """

    def send_mail(self, msg):
        try:
            with smtplib.SMTP(self.SERVER, self.PORT) as server:
                server.send_message(msg)
            logger.info("E-Mail sent successfully !!")
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
