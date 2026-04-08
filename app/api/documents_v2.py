from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from datetime import datetime

from app.core.database import get_db
from app.core.storage import get_storage, S3Storage
from app.services.document_processor import DocumentProcessor
from app.services.document_service import DocumentEnricher, ProtectionDetector
from app.models.document import Document, ManualRefinedDocument, DocumentChunk
from app.models.enums import ProcessingStatus, ProtectionType, ProcessingCapability
from app.schemas.document import (
    DocumentCreate, DocumentUpdate, DocumentResponse, DocumentSearchResult,
    ManualRefinedDocumentCreate, ManualRefinedDocumentResponse
)
from app.schemas.ai import EnrichEvidence, LimitationFlag
from app.core.audit import create_audit_log
from app.models.enums import AuditAction

router = APIRouter()


@router.post("", response_model=DocumentResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    title: str,
    document_type: str,
    customer_id: int,
    file,
    description: Optional[str] = None,
    tags: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    storage: S3Storage = Depends(get_storage)
):
    content = await file.read()
    file_hash = hashlib.sha256(content).hexdigest()
    file_size = len(content)
    
    detector = ProtectionDetector()
    protection_type = await detector.detect(None, content)
    
    file_path = await storage.upload_file(
        file_content=content,
        customer_id=customer_id,
        category="original",
        filename=file.filename or "document",
        content_type=file.content_type
    )
    
    capability = detector.get_processing_capability(protection_type)
    
    if protection_type != ProtectionType.NONE:
        processing_status = ProcessingStatus.PROTECTION_DETECTED
    else:
        processing_status = ProcessingStatus.UPLOADED
    
    import hashlib
    
    document = Document(
        title=title,
        description=description,
        document_type=document_type,
        customer_id=customer_id,
        file_path=file_path,
        file_name=file.filename,
        file_size=file_size,
        file_hash=file_hash,
        mime_type=file.content_type,
        protection_type=protection_type,
        processing_status=processing_status,
        processing_capability=capability,
        tags=tags,
    )
    
    db.add(document)
    await db.commit()
    await db.refresh(document)
    
    await create_audit_log(
        customer_id=customer_id,
        user_id=None,
        action=AuditAction.DOCUMENT_UPLOAD,
        resource_type="document",
        resource_id=str(document.id),
        metadata={"protection_type": protection_type.value}
    )
    
    if protection_type == ProtectionType.NONE:
        background_tasks.add_task(process_document_background, document.id)
    
    return document


async def process_document_background(document_id: int):
    from app.core.database import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        processor = DocumentProcessor(db)
        await processor.process(document_id)


@router.get("/status/{document_id}")
async def get_document_status(
    document_id: int,
    db: AsyncSession = Depends(get_db)
):
    enricher = DocumentEnricher(db)
    return await enricher.get_document_status(document_id)


@router.post("/{document_id}/reprocess")
async def reprocess_document(
    document_id: int,
    db: AsyncSession = Depends(get_db),
    background_tasks: BackgroundTasks = None
):
    result = await db.execute(select(Document).where(Document.id == document_id))
    document = result.scalar_one_or_none()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    await DocumentChunk.filter(DocumentChunk.document_id == document_id).delete()
    
    document.processing_status = ProcessingStatus.UPLOADED
    document.processing_error_reason = None
    await db.commit()
    
    if background_tasks:
        background_tasks.add_task(process_document_background, document_id)
    
    await create_audit_log(
        customer_id=document.customer_id,
        user_id=None,
        action=AuditAction.REPROCESS_REQUEST,
        resource_type="document",
        resource_id=str(document_id)
    )
    
    return {"status": "reprocessing", "document_id": document_id}
