import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging
from src.config import settings
from src.logger import get_logger

logger = get_logger(__name__)

class EmailSender:
    """
    Handles sending emails via SMTP.
    """
    def __init__(self, smtp_server: str = None, smtp_port: int = None, user: str = None, password: str = None):
        self.smtp_server = smtp_server or settings.smtp_server
        self.smtp_port = smtp_port or settings.smtp_port
        self.user = user or settings.email_user
        self.password = password or settings.email_password

    def send_email(self, to_email: str, subject: str, body: str) -> bool:
        """
        Send an email.
        """
        if not self.user or not self.password:
            logger.error("Email credentials not configured for sending.")
            raise ValueError("Email credentials missing.")

        msg = MIMEMultipart()
        msg['From'] = self.user
        msg['To'] = to_email
        msg['Subject'] = subject

        msg.attach(MIMEText(body, 'plain'))

        try:
            print(f"--- SMTP Debug: Connecting to {self.smtp_server}:{self.smtp_port} ---")
            # Create secure connection
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.set_debuglevel(1) # Enable low-level SMTP logs
            server.ehlo()
            server.starttls() # Secure the connection
            server.ehlo()
            
            print(f"--- SMTP Debug: Logging in as {self.user} ---")
            server.login(self.user, self.password)
            
            # Send
            print(f"--- SMTP Debug: Sending to {to_email} ---")
            text = msg.as_string()
            server.sendmail(self.user, to_email, text)
            server.quit()
            
            print("--- SMTP Debug: Email accepted by server ---")
            logger.info(f"Email sent successfully to {to_email}")
            return True
        except Exception as e:
            print(f"--- SMTP ERROR: {e} ---")
            logger.error(f"Failed to send email: {e}")
            raise e
