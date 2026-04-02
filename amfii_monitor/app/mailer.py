import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.mime.text import MIMEText
from pathlib import Path
from datetime import datetime

from app.konstant import config_mail
from app.logger import get_global_logger


class Mailer:

    def __init__(self, config=None):

        config = config or config_mail()

        self.SERVER = config.get("server")
        self.PORT = config.get("port")

        self.FROM = config.get("sender")

        self.RECPTS = config.get("recipients", [])
        self.DEVRECPTS = config.get("dev_recipients", [])

        self.CC = config.get("cc", [])
        self.BCC = config.get("bcc", [])

        self.SEND_MAIL = config.get("send_mail", False)
        self.logger = get_global_logger()


    def send(self,subject,template="CUSTOM",dev=True,attachments=None,**kwargs):
        
        try:

            body_html = Mailer.mail_template(template, **kwargs)

            msg = MIMEMultipart("alternative")
            msg["From"] = self.FROM

            recpts = self.DEVRECPTS if dev else self.RECPTS
            msg["To"] = ", ".join(recpts)
            msg["Subject"] = f"{subject} - {datetime.now():%Y-%m-%d}"

            msg.attach(MIMEText(body_html, "html"))

            if attachments:
                for file in (attachments if isinstance(attachments,list) else [attachments]):
                    if Path(file).exists():
                        with open(file,"rb") as f:
                            part = MIMEApplication(f.read(), Name=Path(file).name)
                            part['Content-Disposition']=f'attachment; filename="{Path(file).name}"'
                            msg.attach(part)

            if not self.SEND_MAIL:
                self.logger.info("Mail Disabled via Config.")
                return

            with smtplib.SMTP(self.SERVER,self.PORT) as server:
                server.send_message(
                    msg,
                    from_addr=self.FROM,
                    to_addrs=recpts+self.CC+self.BCC
                )

            self.logger.info("Email sent.")

        except Exception:
            self.logger.exception("Mailer failed")
            
    @staticmethod
    def mail_template(template: str, **kwargs):

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

        templates = {

            "START": lambda: f"""
            <html><body>
            <p>Hello Team,</p>
            <p><b>{kwargs.get("program")}</b> execution has started.</p>
            <p><b>Start Time:</b> {timestamp}</p>
            <p><b>Codes:</b> {kwargs.get("codes","N/A")}</p>
            </body></html>
            """,

            "SUCCESS": lambda: f"""
            <html><body>
            <p>Hello Team,</p>
            <p><b>{kwargs.get("program")}</b> completed successfully.</p>
            <p><b>Completion Time:</b> {timestamp}</p>
            <p>Output attached.</p>
            </body></html>
            """,

            "ERROR": lambda: f"""
            <html><body>
            <p>Hello Team,</p>
            <p><b>{kwargs.get("program")}</b> failed.</p>
            <p><b>Error:</b> {kwargs.get("error_message")}</p>
            <pre>{kwargs.get("traceback")}</pre>
            </body></html>
            """,

            "CUSTOM": lambda: kwargs.get("custom_html","")

        }

        return templates.get(template, templates["CUSTOM"])()
