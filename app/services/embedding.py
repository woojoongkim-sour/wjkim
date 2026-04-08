import logging
from typing import Optional, List
from openai import AsyncOpenAI
from app.core.config import settings
from app.schemas.ai import Citation, LimitationFlag

logger = logging.getLogger(__name__)


class EmbeddingService:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.OPENAI_EMBEDDING_MODEL
        self.dimension = settings.EMBEDDING_DIMENSION

    async def create_embedding(self, text: str) -> List[float]:
        try:
            response = await self.client.embeddings.create(
                model=self.model,
                input=text[:8000]
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Embedding creation failed: {e}")
            raise

    async def create_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        try:
            response = await self.client.embeddings.create(
                model=self.model,
                input=[t[:8000] for t in texts]
            )
            return [item.embedding for item in response.data]
        except Exception as e:
            logger.error(f"Batch embedding creation failed: {e}")
            raise


embedding_service = EmbeddingService()
