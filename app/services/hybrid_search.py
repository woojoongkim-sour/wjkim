import logging
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, date
import httpx
import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text, and_, or_
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.models.document import Document, DocumentChunk
from app.schemas.search import (
    HybridSearchRequest, HybridSearchResult, HybridSearchResponse,
    VersionSearchRequest, CrossSearchRequest
)

logger = logging.getLogger(__name__)

RRF_K = 60
DENSE_WEIGHT = 0.5
SPARSE_WEIGHT = 0.3
KEYWORD_WEIGHT = 0.2
DENSE_SCORE_THRESHOLD = 0.4


class EmbeddingService:
    def __init__(self):
        self.api_url = settings.EMBEDDING_API_URL
        self.dimension = settings.EMBEDDING_DIMENSION

    async def encode(self, texts: List[str]) -> Tuple[List[List[float]], List[List[float]]]:
        """Generate dense and sparse embeddings using BGE-m3 TEI service."""
        if not texts:
            return [], []
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.api_url}/embed",
                json={"inputs": texts, "truncate": True}
            )
            response.raise_for_status()
            data = response.json()
            
            dense = data.get("dense_embeddings", data.get("embeddings", []))
            sparse = data.get("sparse_embeddings", [])
            
            return dense, sparse


class HybridSearchService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.embedding_service = EmbeddingService()

    async def search(self, request: HybridSearchRequest) -> HybridSearchResponse:
        """Execute 3-way hybrid search with RRF fusion."""
        start_time = datetime.now()
        
        doc_ids = await self._get_valid_document_ids(
            request.customer_id,
            request.include_all_versions,
            request.target_date,
            request.cross_search
        )
        
        if not doc_ids:
            return HybridSearchResponse(
                results=[],
                total=0,
                query_time_ms=0,
                search_mode="single-pass"
            )

        dense_scores, sparse_scores = await self._vector_search(
            request.query, doc_ids
        )
        
        keyword_scores = await self._keyword_search(
            request.query, doc_ids
        )
        
        results = self._fuse_results(
            dense_scores, sparse_scores, keyword_scores,
            request.include_all_versions, request.target_date
        )
        
        filtered_results = self._filter_by_threshold(results)
        
        query_time = (datetime.now() - start_time).total_seconds() * 1000
        
        escalation = len(filtered_results) == 0 or (
            filtered_results and filtered_results[0].dense_score and 
            filtered_results[0].dense_score < DENSE_SCORE_THRESHOLD
        )
        
        return HybridSearchResponse(
            results=filtered_results[:request.limit],
            total=len(filtered_results),
            query_time_ms=query_time,
            search_mode="multi-step" if escalation else "single-pass",
            escalation_triggered=escalation,
            dense_threshold_met=not escalation
        )

    async def _get_valid_document_ids(
        self, customer_id: int, include_all: bool, 
        target_date: Optional[str], cross_search: bool
    ) -> List[int]:
        """Get valid document IDs based on version filtering."""
        query = select(Document.id, Document.customer_id)
        
        if cross_search:
            query = query.where(Document.is_active == True)
        else:
            query = query.where(
                Document.customer_id == customer_id,
                Document.is_active == True
            )
        
        if not include_all and not target_date:
            query = query.where(Document.is_latest == True)
        
        result = await self.db.execute(query)
        return [row[0] for row in result.fetchall()]

    async def _vector_search(
        self, query: str, doc_ids: List[int]
    ) -> Tuple[Dict[int, float], Dict[int, float]]:
        """Execute dense and sparse vector search using pgvector."""
        dense_emb, sparse_emb = await self.embedding_service.encode([query])
        
        if not dense_emb:
            return {}, {}
        
        dense_vector = dense_emb[0]
        
        search_sql = text("""
            SELECT 
                chunk_id,
                (dense_vector <=> :query_vector)::float as dense_score,
                (sparse_vector <=> :sparse_vector)::float as sparse_score
            FROM document_chunks
            WHERE document_id = ANY(:doc_ids)
            ORDER BY dense_vector <=> :query_vector
            LIMIT 100
        """)
        
        result = await self.db.execute(search_sql, {
            "query_vector": str(dense_vector),
            "sparse_vector": str(sparse_emb[0] if sparse_emb else []),
            "doc_ids": doc_ids
        })
        
        dense_scores = {}
        sparse_scores = {}
        for row in result.fetchall():
            chunk_id, d_score, s_score = row
            dense_scores[chunk_id] = max(0, 1 - d_score)
            sparse_scores[chunk_id] = max(0, 1 - s_score) if s_score else 0
        
        return dense_scores, sparse_scores

    async def _keyword_search(
        self, query: str, doc_ids: List[int]
    ) -> Dict[int, float]:
        """Execute keyword search using PGroonga."""
        search_sql = text("""
            SELECT chunk_id,
                   pgroonga_score(document_chunks.id) as keyword_score
            FROM document_chunks,
                 pgroonga_command(
                   'vecslice',
                   json_build_array(
                     pgroonga_command(
                       'query_expand',
                       'columns', json_build_array('content', 'document_title', 'section_title'),
                       'terms', :query
                     )
                   )
                 ) AS query_expanded
            WHERE document_id = ANY(:doc_ids)
              AND content @@ query_expanded::text
            ORDER BY keyword_score DESC
            LIMIT 100
        """)
        
        try:
            result = await self.db.execute(search_sql, {
                "query": query,
                "doc_ids": doc_ids
            })
            
            keyword_scores = {}
            for row in result.fetchall():
                chunk_id, k_score = row
                keyword_scores[chunk_id] = float(k_score) if k_score else 0
            return keyword_scores
        except Exception as e:
            logger.warning(f"PGroonga search failed, falling back: {e}")
            return {}

    def _fuse_results(
        self, dense_scores: Dict[int, float], sparse_scores: Dict[int, float],
        keyword_scores: Dict[int, float], include_all: bool, target_date: Optional[str]
    ) -> List[HybridSearchResult]:
        """Fuse results using Weighted RRF (Reciprocal Rank Fusion)."""
        all_chunk_ids = set(dense_scores.keys()) | set(sparse_scores.keys()) | set(keyword_scores.keys())
        
        dense_ranks = self._get_ranks(dense_scores)
        sparse_ranks = self._get_ranks(sparse_scores)
        keyword_ranks = self._get_ranks(keyword_scores)
        
        results = []
        for chunk_id in all_chunk_ids:
            d_rrf = 1 / (dense_ranks.get(chunk_id, RRF_K) + RRF_K)
            s_rrf = 1 / (sparse_ranks.get(chunk_id, RRF_K) + RRF_K)
            k_rrf = 1 / (keyword_ranks.get(chunk_id, RRF_K) + RRF_K)
            
            final_score = (DENSE_WEIGHT * d_rrf + SPARSE_WEIGHT * s_rrf + KEYWORD_WEIGHT * k_rrf)
            
            results.append({
                "chunk_id": chunk_id,
                "dense_score": dense_scores.get(chunk_id),
                "sparse_score": sparse_scores.get(chunk_id),
                "keyword_score": keyword_scores.get(chunk_id),
                "rank_dense": dense_ranks.get(chunk_id),
                "rank_sparse": sparse_ranks.get(chunk_id),
                "rank_keyword": keyword_ranks.get(chunk_id),
                "final_score": final_score
            })
        
        results.sort(key=lambda x: x["final_score"], reverse=True)
        
        return self._enrich_results(results)

    def _get_ranks(self, scores: Dict[int, float]) -> Dict[int, int]:
        """Convert scores to ranks (1-based)."""
        sorted_items = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return {chunk_id: rank for rank, (chunk_id, _) in enumerate(sorted_items, 1)}

    async def _enrich_results(
        self, scored_results: List[Dict]
    ) -> List[HybridSearchResult]:
        """Enrich results with document information."""
        chunk_ids = [r["chunk_id"] for r in scored_results]
        
        query = select(DocumentChunk, Document).join(
            Document, DocumentChunk.document_id == Document.id
        ).where(DocumentChunk.id.in_(chunk_ids))
        
        result = await self.db.execute(query)
        chunk_map = {}
        for chunk, doc in result.fetchall():
            chunk_map[chunk.id] = chunk
        
        enriched = []
        for scored in scored_results:
            chunk = chunk_map.get(scored["chunk_id"])
            if not chunk:
                continue
            
            enriched.append(HybridSearchResult(
                chunk_id=scored["chunk_id"],
                document_id=chunk.document_id,
                document_title=chunk.document_title or "Untitled",
                section_title=chunk.section_title,
                content=chunk.content[:500] + "..." if len(chunk.content) > 500 else chunk.content,
                customer_id=chunk.customer_id,
                score=scored["final_score"],
                dense_score=scored.get("dense_score"),
                sparse_score=scored.get("sparse_score"),
                keyword_score=scored.get("keyword_score"),
                rank_dense=scored.get("rank_dense"),
                rank_sparse=scored.get("rank_sparse"),
                rank_keyword=scored.get("rank_keyword"),
                version=None,
                is_latest=True,
                created_at=chunk.created_at
            ))
        
        return enriched

    def _filter_by_threshold(self, results: List[HybridSearchResult]) -> List[HybridSearchResult]:
        """Filter results by minimum dense score threshold."""
        return [r for r in results if r.dense_score is None or r.dense_score >= DENSE_SCORE_THRESHOLD]

    async def version_search(self, request: VersionSearchRequest) -> HybridSearchResponse:
        """Execute time-based version search."""
        target = datetime.strptime(request.target_date, "%Y-%m-%d")
        
        version_ids_sql = text("""
            WITH latest_versions AS (
                SELECT DISTINCT ON (version_group_id) 
                    id, version_group_id, version, created_at
                FROM documents
                WHERE version_group_id IS NOT NULL
                  AND created_at <= :target_date
                  AND is_active = true
                ORDER BY version_group_id, version DESC
            )
            SELECT id FROM latest_versions
            UNION ALL
            SELECT id FROM documents
            WHERE version_group_id IS NULL
              AND created_at <= :target_date
              AND is_active = true
        """)
        
        result = await self.db.execute(version_ids_sql, {
            "target_date": target
        })
        valid_doc_ids = [row[0] for row in result.fetchall()]
        
        if not valid_doc_ids:
            return HybridSearchResponse(results=[], total=0, query_time_ms=0, search_mode="single-pass")
        
        request_dict = {
            "query": request.query,
            "customer_id": request.customer_id,
            "include_all_versions": True,
            "limit": request.limit
        }
        
        search_request = HybridSearchRequest(**request_dict)
        return await self.search(search_request)

    async def cross_search(self, request: CrossSearchRequest) -> HybridSearchResponse:
        """Search across all customers for similar cases."""
        search_request = HybridSearchRequest(
            query=request.query,
            customer_id=request.exclude_customer_id or 0,
            cross_search=True,
            limit=request.limit
        )
        return await self.search(search_request)
