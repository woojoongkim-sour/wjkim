from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import uuid


class ImapAccount(Base):
    __tablename__ = "imap_accounts"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False, index=True)
    
    email_address = Column(String(255), nullable=False)
    display_name = Column(String(255))
    
    imap_host = Column(String(255), nullable=False)
    imap_port = Column(Integer, default=993)
    use_ssl = Column(Boolean, default=True)
    username = Column(String(255), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    
    folder = Column(String(255), default="INBOX")
    poll_interval_minutes = Column(Integer, default=15)
    is_active = Column(Boolean, default=True)
    
    last_sync_at = Column(DateTime(timezone=True))
    last_error = Column(Text)
    
    created_by = Column(String(255))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    customer = relationship("Customer", back_populates="imap_accounts")
    collected_emails = relationship("CollectedEmail", back_populates="imap_account")


class CollectedEmail(Base):
    __tablename__ = "collected_emails"

    id = Column(Integer, primary_key=True, index=True)
    imap_account_id = Column(Integer, ForeignKey("imap_accounts.id"), index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), index=True)
    
    message_id = Column(String(500), unique=True, nullable=False, index=True)
    thread_id = Column(String(500), index=True)
    
    subject = Column(String(1000))
    sender_email = Column(String(255))
    sender_name = Column(String(255))
    recipients = Column(Text)  # JSON array
    cc_list = Column(Text)  # JSON array
    
    classification_status = Column(String(20), default="unclassified")  # auto | manual | unclassified
    
    body_text = Column(Text)
    body_html = Column(Text)
    
    received_at = Column(DateTime(timezone=True))
    
    attachments_count = Column(Integer, default=0)
    attachments_info = Column(Text)  # JSON array of attachment metadata
    
    raw_email_path = Column(String(1000))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    imap_account = relationship("ImapAccount", back_populates="collected_emails")
    customer = relationship("Customer")
