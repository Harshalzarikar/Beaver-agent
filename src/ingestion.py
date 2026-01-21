import imaplib
import email
from email.header import decode_header
import logging
from typing import List, Dict, Optional
from datetime import datetime

from src.config import settings
from src.logger import get_logger

logger = get_logger(__name__)

class EmailIngestor:
    """
    Handles secure connection to IMAP servers to fetch and parse emails.
    """
    
    def __init__(self, server: str = None, user: str = None, password: str = None):
        self.imap_server = server or settings.imap_server
        self.user = user or settings.email_user
        self.password = password or settings.email_password
        self.connection = None

    def connect(self):
        """Establish secure SSL connection to IMAP server."""
        if not self.user or not self.password:
            raise ValueError("Email credentials not configured")
            
        try:
            # Create SSL connection
            self.connection = imaplib.IMAP4_SSL(self.imap_server)
            # Login
            self.connection.login(self.user, self.password)
            logger.info(f"Connected to IMAP server: {self.imap_server} as {self.user}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to IMAP: {e}")
            raise ConnectionError(f"Could not connect to {self.imap_server}. Check credentials.")

    def fetch_recent_emails(self, limit: int = 5, folder: str = "INBOX") -> List[Dict]:
        """
        Fetch recent unseen emails from the specified folder.
        
        Returns:
            List[Dict]: List of email objects with 'subject', 'sender', 'date', 'body', 'id'
        """
        if not self.connection:
            self.connect()
            
        emails = []
        try:
            # Select folder (readonly mostly safe)
            status, messages = self.connection.select(folder)
            if status != "OK":
                logger.error(f"Could not open folder: {folder}")
                return []

            # Search for UNSEEN messages
            # Use 'ALL' if you want everything, but 'UNSEEN' is better for workflow
            status, message_ids = self.connection.search(None, "UNSEEN")
            
            if status != "OK":
                return []
                
            email_ids = message_ids[0].split()
            # Get latest 'limit' emails
            latest_ids = email_ids[-limit:]
            
            # Fetch content
            for e_id in reversed(latest_ids):
                # Fetch the email body (RFC822)
                res, msg_data = self.connection.fetch(e_id, "(RFC822)")
                
                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])
                        
                        # Parse Headers
                        subject, encoding = decode_header(msg["Subject"])[0]
                        if isinstance(subject, bytes):
                            subject = subject.decode(encoding or "utf-8")
                            
                        from_ = msg.get("From")
                        date_ = msg.get("Date")
                        
                        # Parse Body
                        body = ""
                        is_html = False
                        
                        if msg.is_multipart():
                            for part in msg.walk():
                                content_type = part.get_content_type()
                                content_disposition = str(part.get("Content-Disposition"))
                                
                                # Skip attachments
                                if "attachment" in content_disposition:
                                    continue
                                
                                try:
                                    # Get text/plain content
                                    if content_type == "text/plain":
                                        body = part.get_payload(decode=True).decode()
                                        is_html = False
                                        break # Prefer plain text
                                    elif content_type == "text/html":
                                        # Fallback to HTML if no plain text found yet
                                        if not body:
                                            body = part.get_payload(decode=True).decode()
                                            is_html = True
                                except:
                                    pass
                        else:
                            # Not multipart
                            body = msg.get_payload(decode=True).decode()
                            content_type = msg.get_content_type()
                            if content_type == "text/html":
                                is_html = True
                        
                        # CLEAN HTML IF NEEDED
                        if is_html and body:
                            try:
                                from bs4 import BeautifulSoup
                                soup = BeautifulSoup(body, "html.parser")
                                # Get text with separator to preserve paragraphs
                                body = soup.get_text(separator="\n").strip()
                                # Clean up excessive newlines
                                import re
                                body = re.sub(r'\n\s*\n', '\n\n', body)
                            except ImportError:
                                logger.warning("BeautifulSoup not found. Returning raw HTML.")
                            except Exception as e:
                                logger.error(f"Failed to clean HTML: {e}")

                        emails.append({
                            "id": e_id.decode(),
                            "subject": subject,
                            "sender": from_,
                            "date": date_,
                            "body": body.strip(),
                            "raw": msg
                        })
                        
            return emails
            
        except Exception as e:
            logger.error(f"Error fetching emails: {e}")
            return []

    def close(self):
        """Close the connection."""
        if self.connection:
            try:
                self.connection.close()
                self.connection.logout()
            except:
                pass
