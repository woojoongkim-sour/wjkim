import logging
import imaplib
import email
from email.header import decode_header
from typing import List, Optional, Dict, Any
from datetime import datetime
import hashlib
import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.email import ImapAccount, CollectedEmail
from app.models.mapping import EmailCustomerMapping, CustomerAlias
from app.models.document import Document
from app.core.config import settings

logger = logging.getLogger(__name__)


class ImapCollector:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def collect_from_account(self, account_id: int) -> Dict[str, Any]:
        """Collect emails from a single IMAP account."""
        result = await self.db.execute(
            select(ImapAccount).where(ImapAccount.id == account_id)
        )
        account = result.scalar_one_or_none()
        
        if not account or not account.is_active:
            return {"status": "error", "message": "Account not found or inactive"}
        
        try:
            emails = self._fetch_emails(account)
            
            processed = 0
            skipped = 0
            for email_data in emails:
                classified = await self._classify_email(email_data, account.customer_id)
                saved = await self._save_email(email_data, account, classified)
                
                if saved:
                    processed += 1
                else:
                    skipped += 1
            
            account.last_sync_at = datetime.utcnow()
            account.last_error = None
            await self.db.commit()
            
            return {
                "status": "success",
                "processed": processed,
                "skipped": skipped,
                "total": len(emails)
            }
            
        except Exception as e:
            logger.error(f"IMAP collection failed for account {account_id}: {e}")
            account.last_error = str(e)
            await self.db.commit()
            return {"status": "error", "message": str(e)}

    def _fetch_emails(self, account: ImapAccount) -> List[Dict[str, Any]]:
        """Fetch emails from IMAP server."""
        emails = []
        
        try:
            if account.use_ssl:
                mail = imaplib.IMAP4_SSL(account.imap_host, account.imap_port)
            else:
                mail = imaplib.IMAP4(account.imap_host, account.imap_port)
            
            mail.login(account.username, self._decrypt_password(account.hashed_password))
            mail.select(account.folder)
            
            status, message_ids = mail.search(None, "ALL")
            
            if status != "OK":
                return emails
            
            for num in message_ids[0].split()[-100:]:
                try:
                    status, msg_data = mail.fetch(num, "(RFC822)")
                    
                    if status == "OK":
                        raw_email = msg_data[0][1]
                        parsed = self._parse_email(raw_email)
                        
                        if parsed:
                            emails.append(parsed)
                            
                except Exception as e:
                    logger.warning(f"Failed to fetch email {num}: {e}")
                    continue
            
            mail.logout()
            
        except Exception as e:
            logger.error(f"IMAP connection failed: {e}")
            raise
        
        return emails

    def _parse_email(self, raw_email: bytes) -> Optional[Dict[str, Any]]:
        """Parse raw email into structured data."""
        try:
            msg = email.message_from_bytes(raw_email)
            
            subject = self._decode_header_value(msg.get("Subject", ""))
            sender = self._parse_address(msg.get("From", ""))
            recipients = self._parse_address_list(msg.get("To", ""))
            cc_list = self._parse_address_list(msg.get("Cc", ""))
            message_id = msg.get("Message-ID", "")
            thread_id = msg.get("References", "").split()[0] if msg.get("References") else message_id
            
            date_str = msg.get("Date", "")
            received_at = self._parse_date(date_str)
            
            body_text, body_html = self._extract_body(msg)
            
            attachments = self._extract_attachments(msg)
            
            return {
                "message_id": message_id,
                "thread_id": thread_id,
                "subject": subject,
                "sender_email": sender["email"],
                "sender_name": sender["name"],
                "recipients": recipients,
                "cc_list": cc_list,
                "body_text": body_text,
                "body_html": body_html,
                "received_at": received_at,
                "attachments": attachments
            }
            
        except Exception as e:
            logger.warning(f"Email parsing failed: {e}")
            return None

    def _decode_header_value(self, header: str) -> str:
        """Decode email header value."""
        if not header:
            return ""
        
        decoded_parts = decode_header(header)
        result = []
        
        for part, encoding in decoded_parts:
            if isinstance(part, bytes):
                result.append(part.decode(encoding or "utf-8", errors="replace"))
            else:
                result.append(part)
        
        return " ".join(result)

    def _parse_address(self, address_str: str) -> Dict[str, str]:
        """Parse email address string."""
        if not address_str:
            return {"email": "", "name": ""}
        
        if "<" in address_str:
            name, email = address_str.rsplit("<", 1)
            return {
                "name": self._decode_header_value(name.strip().strip('"')),
                "email": email.strip().strip(">").strip()
            }
        
        return {"email": address_str.strip(), "name": ""}

    def _parse_address_list(self, address_str: str) -> List[Dict[str, str]]:
        """Parse comma-separated email addresses."""
        if not address_str:
            return []
        
        return [self._parse_address(addr.strip()) for addr in address_str.split(",")]

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse email date string."""
        if not date_str:
            return None
        
        try:
            return email.utils.parsedate_to_datetime(date_str)
        except Exception:
            return None

    def _extract_body(self, msg: email.message.Message) -> tuple[str, str]:
        """Extract text and HTML body from email."""
        text_body = ""
        html_body = ""
        
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                payload = part.get_payload(decode=True)
                
                if not payload:
                    continue
                
                try:
                    decoded = payload.decode("utf-8", errors="replace")
                except:
                    decoded = str(payload)
                
                if content_type == "text/plain":
                    text_body = decoded
                elif content_type == "text/html":
                    html_body = decoded
        else:
            payload = msg.get_payload(decode=True)
            if payload:
                try:
                    decoded = payload.decode("utf-8", errors="replace")
                except:
                    decoded = str(payload)
                
                if msg.get_content_type() == "text/plain":
                    text_body = decoded
                elif msg.get_content_type() == "text/html":
                    html_body = decoded
        
        return text_body, html_body

    def _extract_attachments(self, msg: email.message.Message) -> List[Dict[str, Any]]:
        """Extract attachment information."""
        attachments = []
        
        if msg.is_multipart():
            for part in msg.walk():
                content_disposition = part.get("Content-Disposition", "")
                
                if "attachment" in content_disposition:
                    filename = part.get_filename()
                    if filename:
                        attachments.append({
                            "filename": self._decode_header_value(filename),
                            "content_type": part.get_content_type(),
                            "size": len(part.get_payload(decode=True) or b"")
                        })
        
        return attachments

    def _decrypt_password(self, hashed_password: str) -> str:
        """Decrypt stored password (simplified - in production use proper encryption)."""
        return hashed_password

    async def _classify_email(
        self, email_data: Dict[str, Any], default_customer_id: int
    ) -> Dict[str, Any]:
        """Classify email to customer using multi-stage classification."""
        sender_email = email_data.get("sender_email", "")
        sender_domain = sender_email.split("@")[-1] if sender_email else ""
        subject = email_data.get("subject", "")
        
        mapping = await self._find_email_mapping(sender_email, sender_domain)
        if mapping:
            return {
                "customer_id": mapping.customer_id,
                "status": "auto",
                "method": "email_mapping"
            }
        
        alias = await self._find_customer_alias(subject, default_customer_id)
        if alias:
            return {
                "customer_id": alias.customer_id,
                "status": "auto",
                "method": "subject_alias"
            }
        
        return {
            "customer_id": default_customer_id,
            "status": "unclassified",
            "method": "default"
        }

    async def _find_email_mapping(
        self, email: str, domain: str
    ) -> Optional[EmailCustomerMapping]:
        """Find customer by email address or domain mapping."""
        result = await self.db.execute(
            select(EmailCustomerMapping).where(
                (EmailCustomerMapping.email_pattern == email) |
                (EmailCustomerMapping.email_pattern == domain)
            )
        )
        return result.scalar_one_or_none()

    async def _find_customer_alias(
        self, subject: str, default_customer_id: int
    ) -> Optional[CustomerAlias]:
        """Find customer by alias in email subject."""
        result = await self.db.execute(
            select(CustomerAlias).where(
                CustomerAlias.customer_id == default_customer_id
            )
        )
        aliases = result.scalars().all()
        
        for alias in aliases:
            if alias.alias.lower() in subject.lower():
                return alias
        
        return None

    async def _save_email(
        self, email_data: Dict, account: ImapAccount, classification: Dict
    ) -> bool:
        """Save email to database."""
        result = await self.db.execute(
            select(CollectedEmail).where(
                CollectedEmail.message_id == email_data["message_id"]
            )
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            return False
        
        collected = CollectedEmail(
            imap_account_id=account.id,
            customer_id=classification["customer_id"],
            message_id=email_data["message_id"],
            thread_id=email_data.get("thread_id"),
            subject=email_data["subject"],
            sender_email=email_data["sender_email"],
            sender_name=email_data["sender_name"],
            recipients=json.dumps(email_data.get("recipients", [])),
            cc_list=json.dumps(email_data.get("cc_list", [])),
            classification_status=classification["status"],
            body_text=email_data.get("body_text"),
            body_html=email_data.get("body_html"),
            received_at=email_data.get("received_at"),
            attachments_count=len(email_data.get("attachments", [])),
            attachments_info=json.dumps(email_data.get("attachments", []))
        )
        
        self.db.add(collected)
        
        if email_data.get("body_text"):
            await self._process_email_content(collected, email_data["body_text"])
        
        return True

    async def _process_email_content(self, email_record: CollectedEmail, body_text: str):
        """Process email body content for search/indexing."""
        chunks = self._chunk_text(body_text)
        
        for i, chunk_text in enumerate(chunks):
            normalized = self._normalize_for_dedup(chunk_text)
            content_hash = hashlib.sha256(normalized.encode()).hexdigest()
            
            from app.models.document import DocumentChunk
            from app.services.hybrid_search import EmbeddingService
            
            chunk = DocumentChunk(
                document_id=0,
                customer_id=email_record.customer_id,
                document_title=email_record.subject,
                section_title=None,
                content=chunk_text,
                chunk_index=i,
                content_hash=content_hash,
                metadata_json=json.dumps({
                    "source_type": "imap",
                    "email_id": email_record.id,
                    "message_id": email_record.message_id
                })
            )
            
            self.db.add(chunk)


def _chunk_text(text: str, max_size: int = 1000, overlap: int = 200) -> List[str]:
    """Chunk text for embedding with overlap."""
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + max_size
        
        if end >= len(text):
            chunks.append(text[start:])
            break
        
        chunk = text[start:end]
        
        last_newline = chunk.rfind("\n")
        if last_newline > max_size // 2:
            end = start + last_newline + 1
        
        chunks.append(text[start:end])
        start = end - overlap
    
    return chunks


def _normalize_for_dedup(text: str) -> str:
    """Normalize text for email quote deduplication."""
    lines = text.split("\n")
    normalized_lines = []
    
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(">"):
            continue
        normalized_lines.append(stripped)
    
    normalized = "".join(normalized_lines)
    normalized = "".join(normalized.split())
    
    return normalized.lower()
