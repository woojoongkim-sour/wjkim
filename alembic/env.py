from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from app.core.database import Base
from app.models.customer import Customer, Server, Service
from app.models.document import Document, ManualRefinedDocument, DocumentChunk, DocumentProcessingAttempt, DocumentRelation
from app.models.event import EventOccurrence, EventStateHistory, EventHandlingRecord, EventAssessment, MetricLogEvidence, IncidentCase
from app.models.audit import AuditLog, SanitizedKnowledge
from app.models.associations import document_server_association, document_service_association, service_server_association, incident_case_document_association

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
