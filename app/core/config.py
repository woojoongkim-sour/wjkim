from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/msp_archive"
    SYNC_DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/msp_archive"

    # S3 Storage
    S3_ENDPOINT_URL: str = "http://localhost:9000"
    S3_ACCESS_KEY: str = "minioadmin"
    S3_SECRET_KEY: str = "minioadmin"
    S3_BUCKET_NAME: str = "msp-archive"
    S3_REGION: str = "us-east-1"

    # OpenAI (LLM only - embeddings handled by BGE-m3 TEI)
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o"

    # BGE-m3 Embedding Service (HuggingFace TEI)
    EMBEDDING_API_URL: str = "http://localhost:8080"
    EMBEDDING_DIMENSION: int = 1024

    # Gotenberg (legacy format conversion)
    GOTENBERG_URL: str = "http://localhost:3001"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # Security
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Application
    APP_ENV: str = "development"
    LOG_LEVEL: str = "INFO"

    # Document Processing
    MAX_UPLOAD_SIZE_MB: int = 100
    ALLOWED_EXTENSIONS: list[str] = [
        ".pdf", ".docx", ".doc", ".txt", ".md",
        ".pptx", ".ppt", ".xlsx", ".xls",
        ".hwp", ".hwpx", ".csv",
    ]
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    MAX_EMBEDDING_TEXT_LENGTH: int = 5000

    # Agentic RAG
    AGENT_MAX_TOOL_CALLS: int = 5
    AGENT_TIMEOUT_SECONDS: int = 15
    ESCALATION_SCORE_THRESHOLD: float = 0.5

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"


settings = Settings()
