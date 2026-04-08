from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from app.models.enums import DocumentType, ProtectionType, ProcessingStatus, ProcessingCapability


class DocumentBase(BaseModel):
    title: str = Field(..., max_length=500)
    description: Optional[str] = None
    document_type: DocumentType
    tags: Optional[str] = None


class DocumentCreate(DocumentBase):
    customer_id: int
    file_content: Optional[bytes] = None
    file_name: Optional[str] = None
    metadata_json: Optional[str] = None


class DocumentUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = None
    document_type: Optional[DocumentType] = None
    tags: Optional[str] = None
    metadata_json: Optional[str] = None
    is_active: Optional[bool] = None


class DocumentResponse(DocumentBase):
    id: int
    customer_id: int
    uuid: str
    file_name: Optional[str]
    file_size: Optional[int]
    mime_type: Optional[str]
    protection_type: ProtectionType
    processing_status: ProcessingStatus
    processing_capability: ProcessingCapability
    version: int
    is_active: bool
    is_refined: bool
    processing_error_reason: Optional[str]
    created_by: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


class DocumentSearchResult(BaseModel):
    id: int
    title: str
    document_type: DocumentType
    snippet: Optional[str]
    matched_by: str
    indexing_status: str
    protection_type: ProtectionType
    content_available: bool
    refined_available: bool
    limitation_notice: Optional[str]
    score: float = 0.0

    model_config = {"from_attributes": True}


class ManualRefinedDocumentBase(BaseModel):
    content: str
    summary: Optional[str] = None


class ManualRefinedDocumentCreate(ManualRefinedDocumentBase):
    original_document_id: int


class ManualRefinedDocumentResponse(ManualRefinedDocumentBase):
    id: int
    original_document_id: int
    version: int
    status: str
    approved_by: Optional[str]
    approved_at: Optional[datetime]
    created_by: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}
