import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class EmbeddingResult:
    """Result from TEI embedding service with dense and sparse vectors."""
    dense_vector: List[float]
    sparse_vector: str  # pgvector SPARSEVEC format: {idx:val,...}/dim


class EmbeddingService:
    """TEI-based embedding service using BGE-m3 for dense + sparse embeddings."""

    def __init__(self):
        self.api_url = settings.EMBEDDING_API_URL
        self.dimension = settings.EMBEDDING_DIMENSION
        self.sparse_dim = 250002  # BGE-m3 vocab size

    async def embed_texts(self, texts: List[str]) -> List[EmbeddingResult]:
        """Generate dense and sparse embeddings for a list of texts.
        
        Returns list of EmbeddingResult with .dense_vector and .sparse_vector.
        """
        if not texts:
            return []

        results: List[EmbeddingResult] = []
        dense_vectors: List[List[float]] = []
        sparse_vectors: List[str] = []

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                # Dense embeddings
                response = await client.post(
                    f"{self.api_url}/embed",
                    json={"inputs": texts, "truncate": True}
                )
                response.raise_for_status()
                data = response.json()
                dense_vectors = data if isinstance(data, list) else data.get("embeddings", [])

                # Sparse embeddings
                try:
                    sparse_response = await client.post(
                        f"{self.api_url}/embed_sparse",
                        json={"inputs": texts, "truncate": True}
                    )
                    if sparse_response.status_code == 200:
                        raw_sparse = sparse_response.json()
                        sparse_vectors = [
                            self._format_sparsevec(sv) for sv in raw_sparse
                        ]
                except Exception as e:
                    logger.debug(f"Sparse endpoint not available: {e}")

        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            return []

        # Build results
        for i, text in enumerate(texts):
            dense = dense_vectors[i] if i < len(dense_vectors) else []
            sparse = sparse_vectors[i] if i < len(sparse_vectors) else self._empty_sparsevec()
            results.append(EmbeddingResult(dense_vector=dense, sparse_vector=sparse))

        return results

    async def create_embedding(self, text: str) -> List[float]:
        """Generate a single dense embedding. Convenience method."""
        results = await self.embed_texts([text])
        if results:
            return results[0].dense_vector
        return []

    async def create_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate dense embeddings for a batch. Convenience method."""
        results = await self.embed_texts(texts)
        return [r.dense_vector for r in results]

    def _format_sparsevec(self, sparse_entries: List[Dict[str, Any]]) -> str:
        """Convert TEI sparse format to pgvector SPARSEVEC string.
        
        TEI returns: [{"index": 1234, "value": 0.56}, ...]
        pgvector expects: {1234:0.56, 5678:0.34}/250002
        """
        if not sparse_entries:
            return self._empty_sparsevec()

        parts = []
        for entry in sparse_entries:
            idx = entry.get("index", 0)
            val = entry.get("value", 0.0)
            if val != 0.0:
                parts.append(f"{idx}:{val}")

        return "{" + ",".join(parts) + "}/" + str(self.sparse_dim)

    def _empty_sparsevec(self) -> str:
        return f"{{}}/{self.sparse_dim}"


embedding_service = EmbeddingService()
