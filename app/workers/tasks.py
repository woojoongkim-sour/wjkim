import asyncio
import logging
from app.workers.celery_app import celery_app
from app.core.config import settings

logger = logging.getLogger(__name__)


@celery_app.task(name="process_document", bind=True, max_retries=3)
def process_document_task(self, document_id: int):
    """Process uploaded document: extract text, chunk, embed."""
    try:
        asyncio.run(_process_document(document_id))
    except Exception as e:
        logger.error(f"Document processing failed for {document_id}: {e}")
        raise self.retry(exc=e, countdown=30)


async def _process_document(document_id: int):
    from app.core.database import AsyncSessionLocal
    from app.services.document_processor import DocumentProcessor

    async with AsyncSessionLocal() as session:
        processor = DocumentProcessor(session)
        await processor.process(document_id)


@celery_app.task(name="analyze_event")
def analyze_event_task(event_id: int):
    pass


@celery_app.task(name="cleanup_old_files")
def cleanup_old_files_task():
    pass
