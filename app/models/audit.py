from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
from app.models.enums import AuditAction


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    
    customer_id = Column(Integer, ForeignKey("customers.id"), index=True)
    user_id = Column(String(255), index=True)
    user_email = Column(String(255))
    
    action = Column(String(100), nullable=False, index=True)
    resource_type = Column(String(100))
    resource_id = Column(String(255))
    
    request_path = Column(String(1000))
    request_method = Column(String(10))
    request_params_json = Column(Text)
    request_body_json = Column(Text)
    
    response_status_code = Column(Integer)
    response_summary = Column(Text)
    
    ip_address = Column(String(45))
    user_agent = Column(Text)
    
    metadata_json = Column(Text)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    customer = relationship("Customer")


class SanitizedKnowledge(Base):
    __tablename__ = "sanitized_knowledge"

    id = Column(Integer, primary_key=True, index=True)
    
    source_incident_id = Column(Integer, ForeignKey("incident_cases.id"))
    
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)
    summary = Column(Text)
    
    tags = Column(Text)
    category = Column(String(100))
    
    status = Column(String(50), default="pending")
    approved_by = Column(String(255))
    approved_at = Column(DateTime(timezone=True))
    
    usage_count = Column(Integer, default=0)
    last_used_at = Column(DateTime(timezone=True))
    
    created_by = Column(String(255))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
