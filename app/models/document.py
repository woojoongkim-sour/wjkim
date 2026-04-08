from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text, Enum as SQLEnum, LargeBinary
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
from app.models.enums import ProtectionType, ProcessingStatus, ProcessingCapability, DocumentType
import uuid


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False, index=True)
    
    uuid = Column(String(36), unique=True, default=lambda: str(uuid.uuid4()), index=True)
    
    title = Column(String(500), nullable=False)
    description = Column(Text)
    document_type = Column(SQLEnum(DocumentType), nullable=False)
    
    file_path = Column(String(1000))
    file_name = Column(String(500))
    file_size = Column(Integer)
    file_hash = Column(String(64))
    mime_type = Column(String(100))
    
    protection_type = Column(SQLEnum(ProtectionType), default=ProtectionType.NONE)
    processing_status = Column(SQLEnum(ProcessingStatus), default=ProcessingStatus.UPLOADED)
    processing_capability = Column(SQLEnum(ProcessingCapability), default=ProcessingCapability.METADATA_ONLY)
    
    version = Column(Integer, default=1)
    is_active = Column(Boolean, default=True)
    is_refined = Column(Boolean, default=False)
    
    tags = Column(Text)
    metadata_json = Column(Text)
    processing_error_reason = Column(Text)
    last_processing_attempt_at = Column(DateTime(timezone=True))
    
    created_by = Column(String(255))
    updated_by = Column(String(255))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    customer = relationship("Customer", back_populates="documents")
    refined_documents = relationship("ManualRefinedDocument", back_populates="original_document")
    chunks = relationship("DocumentChunk", back_populates="document")
    processing_attempts = relationship("DocumentProcessingAttempt", back_populates="document")
    relations_as_source = relationship("DocumentRelation", foreign_keys="DocumentRelation.source_document_id", back_populates="source_document")
    relations_as_target = relationship("DocumentRelation", foreign_keys="DocumentRelation.target_document_id", back_populates="target_document")
    servers = relationship("Server", secondary="document_server_association", back_populates="documents")
    services = relationship("Service", secondary="document_service_association", back_populates="documents")


class ManualRefinedDocument(Base):
    __tablename__ = "manual_refined_documents"

    id = Column(Integer, primary_key=True, index=True)
    original_document_id = Column(Integer, ForeignKey("documents.id"), nullable=False, index=True)
    
    content = Column(Text, nullable=False)
    summary = Column(Text)
    
    version = Column(Integer, default=1)
    status = Column(String(50), default="draft")
    approved_by = Column(String(255))
    approved_at = Column(DateTime(timezone=True))
    
    created_by = Column(String(255))
    updated_by = Column(String(255))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    original_document = relationship("Document", back_populates="refined_documents")


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False, index=True)
    
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    embedding = Column(LargeBinary)
    
    metadata_json = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    document = relationship("Document", back_populates="chunks")


class DocumentProcessingAttempt(Base):
    __tablename__ = "document_processing_attempts"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False, index=True)
    
    attempt_type = Column(String(50))
    status = Column(String(50))
    error_message = Column(Text)
    processing_duration_ms = Column(Integer)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    document = relationship("Document", back_populates="processing_attempts")


class DocumentRelation(Base):
    __tablename__ = "document_relations"

    id = Column(Integer, primary_key=True, index=True)
    source_document_id = Column(Integer, ForeignKey("documents.id"), nullable=False, index=True)
    target_document_id = Column(Integer, ForeignKey("documents.id"), nullable=False, index=True)
    
    relation_type = Column(String(100), nullable=False)
    confidence = Column(Integer, default=100)
    source_type = Column(String(50))
    metadata_json = Column(Text)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    source_document = relationship("Document", foreign_keys=[source_document_id], back_populates="relations_as_source")
    target_document = relationship("Document", foreign_keys=[target_document_id], back_populates="relations_as_target")
