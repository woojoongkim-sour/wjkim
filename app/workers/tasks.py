from app.workers.celery_app import celery_app
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.document import Document
from app.core.config import settings
import asyncio

engine = create_engine(settings.SYNC_DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)


@celery_app.task(name="process_document")
def process_document_task(document_id: int):
    from app.services.document_processor import DocumentProcessor
    
    session = SessionLocal()
    try:
        processor = DocumentProcessor(session)
        asyncio.run(processor.process(document_id))
    finally:
        session.close()


@celery_app.task(name="analyze_event")
def analyze_event_task(event_id: int):
    pass


@celery_app.task(name="cleanup_old_files")
def cleanup_old_files_task():
    pass
