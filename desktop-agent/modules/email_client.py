"""
Email client module - IMAP receiving + SMTP sending.
Supports Gmail, Outlook, Yahoo, and any IMAP/SMTP provider.
"""
import smtplib
import imaplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import Dict, Any, List, Optional
from datetime import datetime
import os

from utils.logger import get_logger

log = get_logger("email")


def register(executor, config: dict):
    mod = EmailModule(config)
    
    executor.register_handler("email.send", mod.send_email)
    executor.register_handler("email.read_unread", mod.read_unread)
    executor.register_handler("email.search", mod.search_emails)
    executor.register_handler("email.reply", mod.reply_email)
    executor.register_handler("email.mark_read", mod.mark_read)
    executor.register_handler("email.list_folders", mod.list_folders)


class EmailModule:
    
    def __init__(self, config: dict):
        self.config = config.get("email", {})
        self.imap_server = self.config.get("imap_server", "")
        self.imap_port = self.config.get("imap_port", 993)
        self.imap_ssl = self.config.get("imap_ssl", True)
        self.smtp_server = self.config.get("smtp_server", "")
        self.smtp_port = self.config.get("smtp_port", 587)
        self.smtp_tls = self.config.get("smtp_tls", True)
        self.username = self.config.get("username", "")
        self.password = self.config.get("password", "")
        
        if not self.username or self.password == "${EMAIL_APP_PASSWORD}":
            log.warning("Email credentials not configured - email module limited")
    
    def _imap_connect(self) -> Optional[imaplib.IMAP4_SSL]:
        if not self.username:
            return None
        try:
            if self.imap_ssl:
                conn = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
            else:
                conn = imaplib.IMAP4(self.imap_server, self.imap_port)
            conn.login(self.username, self.password)
            return conn
        except Exception as e:
            log.error(f"IMAP connection failed: {e}")
            return None
    
    async def send_email(self, to: str, subject: str, body: str,
                          cc: Optional[str] = None, bcc: Optional[str] = None,
                          attachments: Optional[List[str]] = None,
                          html: bool = False, **kwargs) -> Dict[str, Any]:
        """Send an email."""
        if not self.username:
            return {"success": False, "error": "Email not configured"}
        
        msg = MIMEMultipart()
        msg["From"] = self.username
        msg["To"] = to
        if cc:
            msg["Cc"] = cc
        msg["Subject"] = subject
        msg["Date"] = email.utils.formatdate(localtime=True)
        
        content_type = "html" if html else "plain"
        msg.attach(MIMEText(body, content_type, "utf-8"))
        
        # Attachments
        if attachments:
            for filepath in attachments:
                if not os.path.exists(filepath):
                    continue
                with open(filepath, "rb") as f:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(f.read())
                    encoders.encode_base64(part)
                    part.add_header(
                        "Content-Disposition",
                        f'attachment; filename="{os.path.basename(filepath)}"'
                    )
                    msg.attach(part)
        
        recipients = [to]
        if cc:
            recipients.append(cc)
        if bcc:
            recipients.append(bcc)
        
        try:
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            if self.smtp_tls:
                server.starttls()
            server.login(self.username, self.password)
            server.sendmail(self.username, recipients, msg.as_string())
            server.quit()
            log.info(f"Email sent to {to}: {subject}")
            return {"success": True, "to": to, "subject": subject}
        except Exception as e:
            log.error(f"Send email failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def read_unread(self, folder: str = "INBOX", limit: int = 10,
                           mark_seen: bool = False, **kwargs) -> Dict[str, Any]:
        """Read unread emails."""
        conn = self._imap_connect()
        if conn is None:
            return {"success": False, "error": "IMAP connection failed"}
        
        try:
            conn.select(folder)
            status, data = conn.search(None, "UNSEEN")
            if status != "OK":
                return {"success": False, "error": "Search failed"}
            
            ids = data[0].split()[:limit]
            emails = []
            for eid in ids:
                status, msg_data = conn.fetch(eid, "(RFC822)")
                if status != "OK":
                    continue
                raw = msg_data[0][1]
                msg = email.message_from_bytes(raw)
                
                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        ct = part.get_content_type()
                        if ct == "text/plain":
                            body = part.get_payload(decode=True).decode(
                                part.get_content_charset() or "utf-8", errors="ignore"
                            )
                            break
                else:
                    body = msg.get_payload(decode=True).decode(
                        msg.get_content_charset() or "utf-8", errors="ignore"
                    )
                
                emails.append({
                    "id": eid.decode(),
                    "from": msg.get("From", ""),
                    "subject": msg.get("Subject", ""),
                    "date": msg.get("Date", ""),
                    "body_preview": body[:500],
                    "body": body,
                    "has_attachments": any(
                        p.get_content_disposition() == "attachment"
                        for p in msg.walk() if msg.is_multipart()
                    ),
                })
                
                if mark_seen:
                    conn.store(eid, "+FLAGS", "\\Seen")
            
            log.info(f"Read {len(emails)} unread emails")
            return {"success": True, "emails": emails, "count": len(emails)}
        except Exception as e:
            return {"success": False, "error": str(e)}
        finally:
            try:
                conn.logout()
            except Exception:
                pass
    
    async def search_emails(self, query: str, folder: str = "INBOX",
                             limit: int = 20, **kwargs) -> Dict[str, Any]:
        """Search emails by query (IMAP SEARCH syntax)."""
        conn = self._imap_connect()
        if conn is None:
            return {"success": False, "error": "IMAP connection failed"}
        
        try:
            conn.select(folder)
            # Try SUBJECT first, fall back to TEXT
            status, data = conn.search(None, 'SUBJECT', f'"{query}"')
            if status != "OK" or not data[0]:
                status, data = conn.search(None, 'TEXT', f'"{query}"')
            
            ids = data[0].split()[:limit] if data[0] else []
            emails = []
            for eid in ids:
                status, msg_data = conn.fetch(eid, "(RFC822)")
                if status != "OK":
                    continue
                msg = email.message_from_bytes(msg_data[0][1])
                emails.append({
                    "id": eid.decode(),
                    "from": msg.get("From", ""),
                    "subject": msg.get("Subject", ""),
                    "date": msg.get("Date", ""),
                })
            return {"success": True, "emails": emails, "count": len(emails)}
        except Exception as e:
            return {"success": False, "error": str(e)}
        finally:
            try:
                conn.logout()
            except Exception:
                pass
    
    async def reply_email(self, message_id: str, body: str,
                           folder: str = "INBOX", **kwargs) -> Dict[str, Any]:
        """Reply to an email by ID."""
        conn = self._imap_connect()
        if conn is None:
            return {"success": False, "error": "IMAP connection failed"}
        
        try:
            conn.select(folder)
            status, msg_data = conn.fetch(message_id.encode(), "(RFC822)")
            if status != "OK":
                return {"success": False, "error": "Message not found"}
            
            msg = email.message_from_bytes(msg_data[0][1])
            from_addr = msg.get("Reply-To", msg.get("From", ""))
            subject = msg.get("Subject", "")
            if not subject.lower().startswith("re:"):
                subject = f"Re: {subject}"
            
            return await self.send_email(to=from_addr, subject=subject, body=body)
        except Exception as e:
            return {"success": False, "error": str(e)}
        finally:
            try:
                conn.logout()
            except Exception:
                pass
    
    async def mark_read(self, message_id: str, folder: str = "INBOX", **kwargs) -> Dict[str, Any]:
        """Mark an email as read."""
        conn = self._imap_connect()
        if conn is None:
            return {"success": False, "error": "IMAP connection failed"}
        try:
            conn.select(folder)
            conn.store(message_id.encode(), "+FLAGS", "\\Seen")
            return {"success": True, "message_id": message_id}
        except Exception as e:
            return {"success": False, "error": str(e)}
        finally:
            try:
                conn.logout()
            except Exception:
                pass
    
    async def list_folders(self, **kwargs) -> Dict[str, Any]:
        """List all email folders."""
        conn = self._imap_connect()
        if conn is None:
            return {"success": False, "error": "IMAP connection failed"}
        try:
            status, folders = conn.list()
            return {"success": True, "folders": [f.decode() for f in folders]}
        except Exception as e:
            return {"success": False, "error": str(e)}
        finally:
            try:
                conn.logout()
            except Exception:
                pass
