from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List, Optional
import hashlib
from datetime import datetime

from app.core.database import get_db
from app.core.storage import get_storage, S3Storage
from app.models.document import Document, ManualRefinedDocument, DocumentChunk, DocumentRelation
from app.models.enums import ProcessingStatus, ProcessingCapability, ProtectionType
from app.schemas.document import (
    DocumentCreate, DocumentUpdate, DocumentResponse, DocumentSearchResult,
    ManualRefinedDocumentCreate, ManualRefinedDocumentResponse
)

router = APIRouter()


@router.post("", response_model=DocumentResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    title: str,
    document_type: str,
    customer_id: int,
    file: UploadFile = File(...),
    description: Optional[str] = None,
    tags: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    storage: S3Storage = Depends(get_storage)
):
    content = await file.read()
    file_hash = hashlib.sha256(content).hexdigest()
    file_size = len(content)
    
    file_path = await storage.upload_file(
        file_content=content,
        customer_id=customer_id,
        category="original",
        filename=file.filename or "document",
        content_type=file.content_type
    )
    
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
        protection_type=ProtectionType.NONE,
        processing_status=ProcessingStatus.UPLOADED,
        tags=tags,
    )
    
    db.add(document)
    await db.commit()
    await db.refresh(document)
    
    background_tasks.add_task(process_document, document.id, db)
    
    return document


async def process_document(document_id: int, db: AsyncSession):
    from app.services.document_processor import DocumentProcessor
    processor = DocumentProcessor(db)
    await processor.process(document_id)


@router.get("", response_model=List[DocumentResponse])
async def list_documents(
    customer_id: Optional[int] = None,
    document_type: Optional[str] = None,
    processing_status: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, le=500),
    db: AsyncSession = Depends(get_db)
):
    query = select(Document).options(selectinload(Document.refined_documents))
    
    if customer_id:
        query = query.where(Document.customer_id == customer_id)
    if document_type:
        query = query.where(Document.document_type == document_type)
    if processing_status:
        query = query.where(Document.processing_status == processing_status)
    
    query = query.where(Document.is_active == True)
    query = query.offset(skip).limit(limit).order_by(Document.created_at.desc())
    
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(document_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Document)
        .options(selectinload(Document.refined_documents))
        .where(Document.id == document_id)
    )
    document = result.scalar_one_or_none()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return document


@router.put("/{document_id}", response_model=DocumentResponse)
async def update_document(
    document_id: int,
    document_update: DocumentUpdate,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Document).where(Document.id == document_id))
    db_document = result.scalar_one_or_none()
    if not db_document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    update_data = document_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_document, key, value)
    
    await db.commit()
    await db.refresh(db_document)
    return db_document


@router.delete("/{document_id}")
async def delete_document(document_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Document).where(Document.id == document_id))
    document = result.scalar_one_or_none()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    document.is_active = False
    await db.commit()
    return {"status": "deleted"}


@router.post("/{document_id}/refined", response_model=ManualRefinedDocumentResponse)
async def upload_refined_document(
    document_id: int,
    refined: ManualRefinedDocumentCreate,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Document).where(Document.id == document_id))
    document = result.scalar_one_or_none()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    db_refined = ManualRefinedDocument(
        original_document_id=document_id,
        content=refined.content,
        summary=refined.summary,
    )
    
    document.is_refined = True
    document.processing_status = ProcessingStatus.REFINED_UPLOADED
    document.processing_capability = ProcessingCapability.FULLTEXT_EXTRACTABLE
    
    db.add(db_refined)
    await db.commit()
    await db.refresh(db_refined)
    return db_refined


@router.get("/{document_id}/refined", response_model=List[ManualRefinedDocumentResponse])
async def list_refined_documents(
    document_id: int,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(ManualRefinedDocument)
        .where(ManualRefinedDocument.original_document_id == document_id)
        .order_by(ManualRefinedDocument.version.desc())
    )
    return result.scalars().all()


@router.get("/{document_id}/download")
async def download_document(
    document_id: int,
    db: AsyncSession = Depends(get_db),
    storage: S3Storage = Depends(get_storage)
):
    result = await db.execute(select(Document).where(Document.id == document_id))
    document = result.scalar_one_or_none()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    if not document.file_path:
        raise HTTPException(status_code=404, detail="File not found")
    
    url = await storage.get_presigned_url(document.file_path)
    return {"download_url": url}
