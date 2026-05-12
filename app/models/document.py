from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text, Enum as SQLEnum, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector, SPARSEVEC
from app.core.database import Base
from app.models.enums import ProtectionType, ProcessingStatus, ProcessingCapability, DocumentType
import uuid


class DocumentCategory(Base):
    __tablename__ = "document_categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    code = Column(String(100), unique=True, nullable=False)
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    documents = relationship("Document", back_populates="category")


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False, index=True)
    category_id = Column(Integer, ForeignKey("document_categories.id"), index=True)

    uuid = Column(String(36), unique=True, default=lambda: str(uuid.uuid4()), index=True)

    title = Column(String(500), nullable=False)
    description = Column(Text)
    # Keep document_type enum for backward compat; prefer category_id for new code
    document_type = Column(SQLEnum(DocumentType), nullable=False)

    original_filename = Column(String(500))
    file_path = Column(String(1000))
    file_name = Column(String(500))
    file_size = Column(Integer)
    content_hash = Column(String(64), index=True)  # SHA-256
    file_type = Column(String(50))  # pdf, docx, hwp, etc.
    mime_type = Column(String(100))
    source_type = Column(String(20), default="upload")  # upload | imap

    protection_type = Column(SQLEnum(ProtectionType), default=ProtectionType.NONE)
    processing_status = Column(SQLEnum(ProcessingStatus), default=ProcessingStatus.UPLOADED, index=True)
    processing_capability = Column(SQLEnum(ProcessingCapability), default=ProcessingCapability.METADATA_ONLY)
    meta_only = Column(Boolean, default=False)

    # Version management
    version_group_id = Column(String(36), index=True)  # UUID grouping versions
    version = Column(Integer, default=1)
    is_latest = Column(Boolean, default=True, index=True)

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
    category = relationship("DocumentCategory", back_populates="documents")
    refined_documents = relationship("ManualRefinedDocument", back_populates="original_document")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")
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
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False, index=True)  # denormalized

    document_title = Column(String(500))  # denormalized for PGroonga keyword search
    section_title = Column(String(500))
    content = Column(Text, nullable=False)
    chunk_index = Column(Integer, nullable=False)
    token_count = Column(Integer)

    content_hash = Column(String(64))  # email chunk dedup (NULL for normal docs)

    dense_vector = Column(Vector(1024))  # BGE-m3 dense embedding
    sparse_vector = Column(SPARSEVEC(250002))  # BGE-m3 sparse embedding (vocab size)

    metadata_json = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    document = relationship("Document", back_populates="chunks")

    # PGroonga and HNSW indexes are created via raw SQL in migration (init.sql)
    # Email chunk dedup index also created in migration


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
