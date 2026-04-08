import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.models.document import Document, DocumentChunk, DocumentProcessingAttempt, ManualRefinedDocument
from app.models.enums import ProcessingStatus, ProcessingCapability, ProtectionType
from app.core.config import settings
from typing import Optional
import hashlib

logger = logging.getLogger(__name__)


class DocumentProcessor:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def process(self, document_id: int):
        logger.info(f"Processing document {document_id}")
        
        result = await self.db.execute(
            select(Document).where(Document.id == document_id)
        )
        document = result.scalar_one_or_none()
        
        if not document:
            logger.error(f"Document {document_id} not found")
            return
        
        attempt = DocumentProcessingAttempt(
            document_id=document_id,
            attempt_type="full_processing"
        )
        self.db.add(attempt)
        
        try:
            document.processing_status = ProcessingStatus.METADATA_EXTRACTED
            document.protection_type = ProtectionType.NONE
            
            has_refined = await self._check_refined(document)
            if has_refined:
                document.is_refined = True
                document.processing_capability = ProcessingCapability.FULLTEXT_EXTRACTABLE
                document.processing_status = ProcessingStatus.REFINED_UPLOADED
                logger.info(f"Document {document_id} has refined content")
                await self.db.commit()
                return
            
            content = await self._extract_content(document)
            
            if not content:
                document.processing_status = ProcessingStatus.AWAITING_MANUAL_REFINEMENT
                document.processing_capability = ProcessingCapability.MANUAL_REFINED_ONLY
                logger.warning(f"Document {document_id} requires manual refinement")
                await self.db.commit()
                return
            
            chunks = self._chunk_content(content)
            await self._create_chunks(document, chunks)
            
            embedding = await self._create_embedding(content)
            if embedding:
                document.processing_capability = ProcessingCapability.EMBEDDABLE
                document.processing_status = ProcessingStatus.READY_FOR_VECTOR
            
            document.processing_status = ProcessingStatus.READY_FOR_SEARCH
            attempt.status = "success"
            logger.info(f"Document {document_id} processed successfully")
            
        except Exception as e:
            logger.error(f"Error processing document {document_id}: {e}")
            document.processing_status = ProcessingStatus.PROCESSING_FAILED
            document.processing_error_reason = str(e)
            attempt.status = "failed"
            attempt.error_message = str(e)
        
        await self.db.commit()
    
    async def _check_refined(self, document: Document) -> bool:
        result = await self.db.execute(
            select(ManualRefinedDocument)
            .where(ManualRefinedDocument.original_document_id == document.id)
            .limit(1)
        )
        return result.scalar_one_or_none() is not None
    
    async def _extract_content(self, document: Document) -> Optional[str]:
        if not document.file_path:
            return None
        
        try:
            if document.mime_type == "text/plain":
                return "Text content extraction placeholder"
            elif document.mime_type in ["application/pdf", "application/msword"]:
                return "Document content extraction placeholder"
            else:
                return "Generic content extraction"
        except Exception as e:
            logger.error(f"Content extraction failed: {e}")
            return None
    
    def _chunk_content(self, content: str) -> list[str]:
        chunks = []
        chunk_size = settings.CHUNK_SIZE
        overlap = settings.CHUNK_OVERLAP
        
        for i in range(0, len(content), chunk_size - overlap):
            chunk = content[i:i + chunk_size]
            if chunk:
                chunks.append(chunk)
        
        return chunks or [content]
    
    async def _create_chunks(self, document: Document, chunks: list[str]):
        for idx, chunk_text in enumerate(chunks):
            chunk = DocumentChunk(
                document_id=document.id,
                chunk_index=idx,
                content=chunk_text,
                metadata_json='{"source": "auto_extracted"}'
            )
            self.db.add(chunk)
    
    async def _create_embedding(self, content: str) -> Optional[bytes]:
        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI()
            
            response = await client.embeddings.create(
                model=settings.OPENAI_EMBEDDING_MODEL,
                input=content[:1000]
            )
            
            embedding = response.data[0].embedding
            import pickle
            return pickle.dumps(embedding)
            
        except Exception as e:
            logger.error(f"Embedding creation failed: {e}")
            return None
