#!/usr/bin/env python3
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from alembic.config import Config
from alembic import command
from app.core.database import sync_engine
from app.core.database import Base
from app.models.customer import Customer, Server, Service
from app.models.document import Document, ManualRefinedDocument, DocumentChunk, DocumentProcessingAttempt, DocumentRelation
from app.models.event import EventOccurrence, EventStateHistory, EventHandlingRecord, EventAssessment, MetricLogEvidence, IncidentCase
from app.models.audit import AuditLog, SanitizedKnowledge
from app.models.associations import document_server_association, document_service_association, service_server_association, incident_case_document_association


def run_migrations():
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")


def init_db():
    Base.metadata.create_all(bind=sync_engine)
    print("Database tables created successfully!")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "migrate":
        run_migrations()
    else:
        init_db()
