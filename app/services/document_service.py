import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.document import Document, ManualRefinedDocument
from app.models.enums import ProtectionType, ProcessingStatus, ProcessingCapability

logger = logging.getLogger(__name__)


class ProtectionDetector:
    PROTECTED_MIME_TYPES = {
        "application/pdf": [".pdf"],
        "application/vnd.ms-excel": [".xls", ".xlsx"],
        "application/vnd.openxmlformats-officedocument.spreadsheetml": [".xlsx"],
    }
    
    PASSWORD_INDICATORS = [
        b"Encrypt",
        b"password",
        b"encrypted",
    ]

    async def detect(self, document: Document, file_content: bytes) -> ProtectionType:
        if document.mime_type in self.PROTECTED_MIME_TYPES:
            if self._has_encryption_marker(file_content):
                return ProtectionType.PASSWORD_PROTECTED
            
            if document.file_size and document.file_size < 1000:
                return ProtectionType.UNKNOWN
        
        return ProtectionType.NONE

    def _has_encryption_marker(self, content: bytes) -> bool:
        for indicator in self.PASSWORD_INDICATORS:
            if indicator.lower() in content[:5000].lower():
                return True
        return False

    def get_processing_capability(self, protection: ProtectionType) -> ProcessingCapability:
        if protection == ProtectionType.NONE:
            return ProcessingCapability.FULLTEXT_EXTRACTABLE
        elif protection in [ProtectionType.PASSWORD_PROTECTED, ProtectionType.DRM_PROTECTED]:
            return ProcessingCapability.MANUAL_REFINED_ONLY
        else:
            return ProcessingCapability.METADATA_ONLY


class DocumentEnricher:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_document_status(self, document_id: int) -> dict:
        result = await self.db.execute(
            select(Document).where(Document.id == document_id)
        )
        document = result.scalar_one_or_none()
        
        if not document:
            return {"error": "Document not found"}
        
        status = {
            "id": document.id,
            "title": document.title,
            "protection_type": document.protection_type,
            "processing_status": document.processing_status,
            "processing_capability": document.processing_capability,
            "is_refined": document.is_refined,
            "content_available": document.processing_capability in [
                ProcessingCapability.FULLTEXT_EXTRACTABLE,
                ProcessingCapability.CHUNKABLE,
                ProcessingCapability.EMBEDDABLE,
            ],
            "limitation": self._get_limitation(document)
        }
        
        if document.is_refined:
            refined_result = await self.db.execute(
                select(ManualRefinedDocument)
                .where(ManualRefinedDocument.original_document_id == document.id)
                .order_by(ManualRefinedDocument.version.desc())
                .limit(1)
            )
            refined = refined_result.scalar_one_or_none()
            if refined:
                status["refined_content_available"] = True
                status["refined_version"] = refined.version
        
        return status

    def _get_limitation(self, document: Document) -> Optional[str]:
        if document.protection_type != ProtectionType.NONE:
            return f"Protected by {document.protection_type.value}"
        
        if document.processing_status == ProcessingStatus.AWAITING_MANUAL_REFINEMENT:
            return "Awaiting manual refinement"
        
        if not document.is_refined and document.processing_capability == ProcessingCapability.MANUAL_REFINED_ONLY:
            return "Manual refinement recommended for full access"
        
        return None
