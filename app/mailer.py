import smtplib, logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

from app.konstant import MAIL_CONFIG
from app.logger import get_global_logger

logger = get_global_logger()


class Mailer:
    def __init__(self, server='172.17.0.126', port=25, sender='Kaustubh.Keny@cogencis.com', recipients=['Kaustubh.Keny@cogencis.com'], cc=None, bcc=None, logger=None):
        
        mail_config = MAIL_CONFIG
        recipients = mail_config.get("recipients", recipients)
        cc = mail_config.get("cc", cc)
        bcc = mail_config.get("bcc", bcc)
    
        self.SERVER = mail_config.get("server", server)
        self.PORT = mail_config.get("port", port)
        self.FROM = mail_config.get("sender", sender)
        self.RECPTS = recipients if isinstance(recipients, list) else [recipients] if recipients else []
        self.CC = cc if isinstance(cc, list) else [cc] if cc else []
        self.BCC = bcc if isinstance(bcc, list) else [bcc] if bcc else []
        
        self.logger = logger or logging.getLogger(__name__)


    def started(self, program, data=None):
        subject = f"{program} — Execution Started"
        body = f"""
        <html>
            <body>
                <p>Hello Team,</p>
                <p>The program <b>{program}</b> has <b>started</b>.</p>
                <p>Files attatched are {','.join(data)}</p>
                <p>Regards,<br>Kaustubh</p>
            </body>
        </html>
        """
        msg = self.construct_mail(subject=subject, body_html=body)
        self.send_mail(msg)
   
    def end(self, program, data=None):
        subject = f"{program} — Execution Completed"
        process, failed = data

        completed_amcs = '<br>'.join(process)
        failed_amcs = '<br>'.join(failed)
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

    def default_body(self):
        return """
        <html>
            <body>
                <p>Hello Team,</p>
                <p>This is Default Mail Message.</p>
                <p>Regards,<br>System</p>
            </body>
        </html>
        """
    
    def send_custom(self, subject, body_html=None, body_text=None):
        msg = self.construct_mail(subject=subject, body_html=body_html, body_text=body_text)
        self.send_mail(msg)
    
    def construct_mail(self, subject, body_html=None, body_text=None):
        msg = MIMEMultipart("alternative")
        msg["From"] = self.FROM
        msg["To"] = ", ".join(self.RECPTS)
        if self.CC:
            msg["Cc"] = ", ".join(self.CC)
        msg["Subject"] = f"{subject} - {datetime.now().strftime('%Y-%m-%d')}"

        if body_text:
            msg.attach(MIMEText(body_text, "plain"))
        if body_html:
            msg.attach(MIMEText(body_html, "html"))
        else:
            msg.attach(MIMEText(self.default_body(), "html"))

        return msg


    def send_mail(self, msg):
        try:
            all_recipients = self.RECPTS + self.CC + self.BCC
            with smtplib.SMTP(self.SERVER, self.PORT) as server:
                server.send_message(msg, from_addr=self.FROM, to_addrs=all_recipients)
            # self.logger.info("Email sent successfully.")
        except Exception as e:
            self.logger.error(f"Failed to send email: {e}")

    def test_connection(self):
        try:
            with smtplib.SMTP(self.SERVER, self.PORT) as server:
                server.noop()
            print("SMTP connection successful.")
        except Exception as e:
            print(f"SMTP connection failed: {e}")
