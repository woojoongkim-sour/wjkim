import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
import math
import asyncio

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.models.document import Document, DocumentChunk
from app.services.embedding import EmbeddingService

logger = logging.getLogger(__name__)


@dataclass
class SearchScores:
    dense: float
    sparse: float
    keyword: float
    recency: float


@dataclass
class SearchResult:
    chunk_id: int
    document_id: int
    document_title: str
    section_title: Optional[str]
    content: str
    customer_id: int
    score: float
    scores: SearchScores
    snippet: str


@dataclass
class SearchFilters:
    category_ids: Optional[List[int]] = None
    file_types: Optional[List[str]] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None


class HybridSearchService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.embedding_service = EmbeddingService()

    async def _sanitize_filters(self, filters: Optional[SearchFilters]) -> Dict[str, Any]:
        if not filters:
            return {}
        params: Dict[str, Any] = {}
        if filters.category_ids:
            category_ids = [cid for cid in filters.category_ids if isinstance(cid, int) and cid > 0]
            if category_ids:
                params["category_ids"] = category_ids
        if filters.file_types:
            allowed = {"pdf", "doc", "docx", "txt", "md", "html", "epub"}
            file_types = [ft.lower() for ft in filters.file_types if isinstance(ft, str) and ft.lower() in allowed]
            if file_types:
                params["file_types"] = file_types
        if filters.date_from or filters.date_to:
            date_from = filters.date_from
            date_to = filters.date_to
            if date_from and date_to:
                try:
                    df = datetime.fromisoformat(date_from)
                    dto = datetime.fromisoformat(date_to)
                    if df == dto:
                        dto = df + timedelta(days=1)
                        date_to = dto.isoformat()
                    date_from = df.isoformat()
                    date_to = dto.isoformat()
                except Exception:
                    pass
            if date_from:
                params["date_from"] = date_from
            if date_to:
                params["date_to"] = date_to
        return params

    async def search(
        self,
        query: str,
        customer_id: int,
        filters: Optional[SearchFilters] = None,
        limit: int = 20,
        include_all_versions: bool = False,
    ) -> List[SearchResult]:
        embedding = await self.embedding_service.embed_texts([query])
        dense_vector: List[float] = []
        sparse_vector: Dict[str, float] = {}
        if embedding and len(embedding) > 0:
            res = embedding[0]
            dense_vector = getattr(res, "dense_vector", []) or []
            sparse_vector = getattr(res, "sparse_vector", {}) or {}

        san_filters = await self._sanitize_filters(filters)

        async def _exec(sql: str, params: Dict[str, Any]) -> List[Dict[str, Any]]:
            result = await self.db.execute(text(sql), params)
            return list(result.mappings().all())

        # Dense
        dense_sql = (
            "SELECT dc.id AS chunk_id, dc.document_id, d.title AS document_title, dc.section_title, dc.content, "
            "d.customer_id AS customer_id, d.created_at AS created_at, "
            "(1 - (dc.dense_vector <=> :query_vector)) AS dense_score "
            "FROM document_chunks AS dc JOIN documents AS d ON dc.document_id = d.id "
        )
        dense_sql += " WHERE d.customer_id = :cid "
        dense_params: Dict[str, Any] = {"cid": customer_id, "query_vector": dense_vector}
        if not include_all_versions:
            dense_sql += " AND d.is_latest = TRUE"
        if san_filters.get("category_ids"):
            dense_sql += " AND d.category_id = ANY(:category_ids)"
            dense_params["category_ids"] = san_filters["category_ids"]
        if san_filters.get("file_types"):
            dense_sql += " AND d.file_type = ANY(:file_types)"
            dense_params["file_types"] = san_filters["file_types"]
        if san_filters.get("date_from"):
            dense_sql += " AND d.created_at >= :date_from"
            dense_params["date_from"] = san_filters["date_from"]
        if san_filters.get("date_to"):
            dense_sql += " AND d.created_at <= :date_to"
            dense_params["date_to"] = san_filters["date_to"]
        dense_sql += " ORDER BY dense_score DESC LIMIT :limit"
        dense_params["limit"] = limit
        # Run dense, sparse and keyword channels in parallel
        dense_task = _exec(dense_sql, dense_params)
        # Sparse
        sparse_sql = (
            "SELECT dc.id AS chunk_id, dc.document_id, d.title AS document_title, dc.section_title, dc.content, "
            "d.customer_id AS customer_id, d.created_at AS created_at, "
            "(1 - (dc.sparse_vector <=> :query_sparse)) AS sparse_score "
            "FROM document_chunks AS dc JOIN documents AS d ON dc.document_id = d.id "
        )
        sparse_sql += " WHERE d.customer_id = :cid "
        sparse_params: Dict[str, Any] = {"cid": customer_id, "query_sparse": sparse_vector}
        if not include_all_versions:
            sparse_sql += " AND d.is_latest = TRUE"
        if san_filters.get("category_ids"):
            sparse_sql += " AND d.category_id = ANY(:category_ids)"
            sparse_params["category_ids"] = san_filters["category_ids"]
        if san_filters.get("file_types"):
            sparse_sql += " AND d.file_type = ANY(:file_types)"
            sparse_params["file_types"] = san_filters["file_types"]
        if san_filters.get("date_from"):
            sparse_sql += " AND d.created_at >= :date_from"
            sparse_params["date_from"] = san_filters["date_from"]
        if san_filters.get("date_to"):
            sparse_sql += " AND d.created_at <= :date_to"
            sparse_params["date_to"] = san_filters["date_to"]
        sparse_sql += " ORDER BY sparse_score DESC LIMIT :limit"
        sparse_params["limit"] = limit
        keyword_sql = (
            "SELECT dc.id AS chunk_id, dc.document_id, d.title AS document_title, dc.section_title, dc.content, "
            "d.customer_id AS customer_id, d.created_at AS created_at, "
            "pgroonga_score('document_chunks'::regclass, dc.ctid) AS keyword_score "
            "FROM document_chunks AS dc JOIN documents AS d ON dc.document_id = d.id "
        )
        keyword_sql += " WHERE d.customer_id = :cid AND (dc.content &@~ :query OR d.title &@~ :query OR dc.section_title &@~ :query) "
        keyword_sql += " ORDER BY keyword_score DESC LIMIT :limit"
        keyword_params: Dict[str, Any] = {"cid": customer_id, "query": query, "limit": limit}
        keyword_task = _exec(keyword_sql, keyword_params)
        try:
            dense_rows, sparse_rows, keyword_rows = await asyncio.gather(dense_task, _exec(sparse_sql, sparse_params), keyword_task, return_exceptions=True)
            if isinstance(dense_rows, Exception):
                logger.error(f"Dense search failed: {dense_rows}")
                dense_rows = []
            if isinstance(sparse_rows, Exception):
                logger.error(f"Sparse search failed: {sparse_rows}")
                sparse_rows = []
            if isinstance(keyword_rows, Exception):
                logger.error(f"Keyword search failed: {keyword_rows}")
                keyword_rows = []
        except Exception as e:
            logger.error(f"Search channels failed to start: {e}")
            dense_rows, sparse_rows, keyword_rows = [], [], []

        def _rank_map(rows: List[Dict[str, Any]]) -> Dict[int, int]:
            rank = {}
            for i, r in enumerate(rows, start=1):
                rank[int(r["chunk_id"])] = i
            return rank

        dense_rank = _rank_map(dense_rows)
        sparse_rank = _rank_map(sparse_rows)
        keyword_rank = _rank_map(keyword_rows)

        all_keys = set(list(dense_rank.keys()) + list(sparse_rank.keys()) + list(keyword_rank.keys()))
        merged: List[tuple] = []
        for chunk_id in all_keys:
            payload = {}
            for src in (dense_rows, sparse_rows, keyword_rows):
                for row in src:
                    if int(row["chunk_id"]) == int(chunk_id):
                        payload = row
                        break
            merged.append((int(chunk_id), payload))

        results: List[SearchResult] = []
        now = datetime.utcnow()
        scored: List[Dict[str, Any]] = []
        for chunk_id, payload in merged:
            dense_score = None
            sparse_score = None
            keyword_score = None
            created_at = payload.get("created_at") if isinstance(payload, dict) else None
            if dense_rows:
                for r in dense_rows:
                    if int(r["chunk_id"]) == chunk_id:
                        dense_score = float(r.get("dense_score", 0.0))
                        break
            if sparse_rows:
                for r in sparse_rows:
                    if int(r["chunk_id"]) == chunk_id:
                        sparse_score = float(r.get("sparse_score", 0.0))
                        break
            if keyword_rows:
                for r in keyword_rows:
                    if int(r["chunk_id"]) == chunk_id:
                        keyword_score = float(r.get("keyword_score", 0.0))
                        break
            dense_score = 0.0 if dense_score is None else dense_score
            sparse_score = 0.0 if sparse_score is None else sparse_score
            keyword_score = 0.0 if keyword_score is None else keyword_score
            recency = 0.0
            if created_at:
                try:
                    created = created_at if isinstance(created_at, datetime) else datetime.fromisoformat(str(created_at))
                    days = (now - created).days
                    recency = math.exp(-days / 365.0)
                except Exception:
                    recency = 0.0
            dense_rrf = 1.0 / (dense_rank.get(chunk_id, 999999) + 60) if dense_score is not None else 0.0
            sparse_rrf = 1.0 / (sparse_rank.get(chunk_id, 999999) + 60) if sparse_score is not None else 0.0
            keyword_rrf = 1.0 / (keyword_rank.get(chunk_id, 999999) + 60) if keyword_score is not None else 0.0
            final_rrf = 0.5 * dense_rrf + 0.3 * sparse_rrf + 0.2 * keyword_rrf
            scored.append({
                "chunk_id": chunk_id,
                "document_id": payload.get("document_id") or 0,
                "document_title": payload.get("document_title") or "",
                "section_title": payload.get("section_title"),
                "content": payload.get("content") or "",
                "customer_id": payload.get("customer_id") or 0,
                "created_at": created_at,
                "final_rrf": final_rrf,
                "dense_score": dense_score or 0.0,
                "sparse_score": sparse_score or 0.0,
                "keyword_score": keyword_score or 0.0,
                "recency": recency,
            })
        if scored:
            min_fs = min(item["final_rrf"] for item in scored)
            max_fs = max(item["final_rrf"] for item in scored)
            range_fs = max_fs - min_fs
            for item in scored:
                norm = 0.0 if range_fs == 0 else (item["final_rrf"] - min_fs) / range_fs
                snippet = (item["content"][:200] + "...") if len(item["content"]) > 200 else item["content"]
                results.append(
                    SearchResult(
                        chunk_id=item["chunk_id"],
                        document_id=item["document_id"] or 0,
                        document_title=item["document_title"] or "",
                        section_title=item["section_title"],
                        content=item["content"],
                        customer_id=item["customer_id"],
                        score=float(norm),
                        scores=SearchScores(
                            dense=float(item["dense_score"] or 0.0),
                            sparse=float(item["sparse_score"] or 0.0),
                            keyword=float(item["keyword_score"] or 0.0),
                            recency=float(item["recency"] or 0.0),
                        ),
                        snippet=snippet,
                    )
                )
        results.sort(key=lambda r: (r.score, r.document_title), reverse=True)
        if len(results) > limit:
            results = results[:limit]
        return results

    async def cross_search(self, query: str, filters: Optional[SearchFilters] = None, limit: int = 20) -> List[SearchResult]:
        embedding = await self.embedding_service.embed_texts([query])
        dense_vector = (embedding[0].dense_vector if embedding and len(embedding) > 0 else [])
        sparse_vector = (embedding[0].sparse_vector if embedding and len(embedding) > 0 else {})
        san_filters = await self._sanitize_filters(filters)

        async def _exec(sql: str, params: Dict[str, Any]) -> List[Dict[str, Any]]:
            result = await self.db.execute(text(sql), params)
            return list(result.mappings().all())

        dense_sql = (
            "SELECT dc.id AS chunk_id, dc.document_id, d.title AS document_title, dc.section_title, dc.content, "
            "d.customer_id AS customer_id, d.created_at AS created_at, "
            "(1 - (dc.dense_vector <=> :query_vector)) AS dense_score "
            "FROM document_chunks AS dc JOIN documents AS d ON dc.document_id = d.id "
            "WHERE 1=1 "
        )
        dense_sql += " ORDER BY dense_score DESC LIMIT :limit"
        dense_params = {"query_vector": dense_vector, "limit": limit}
        try:
            dense_rows = await _exec(dense_sql, dense_params)
        except Exception as e:
            logger.error(f"Cross-dense search failed: {e}")
            dense_rows = []

        sparse_sql = (
            "SELECT dc.id AS chunk_id, dc.document_id, d.title AS document_title, dc.section_title, dc.content, "
            "d.customer_id AS customer_id, d.created_at AS created_at, "
            "(1 - (dc.sparse_vector <=> :query_sparse)) AS sparse_score "
            "FROM document_chunks AS dc JOIN documents AS d ON dc.document_id = d.id "
            "ORDER BY sparse_score DESC LIMIT :limit"
        )
        sparse_params = {"query_sparse": sparse_vector, "limit": limit}
        try:
            sparse_rows = await _exec(sparse_sql, sparse_params)
        except Exception as e:
            logger.error(f"Cross-sparse search failed: {e}")
            sparse_rows = []

        keyword_sql = (
            "SELECT dc.id AS chunk_id, dc.document_id, d.title AS document_title, dc.section_title, dc.content, "
            "d.customer_id AS customer_id, d.created_at AS created_at, "
            "pgroonga_score('document_chunks'::regclass, dc.ctid) AS keyword_score "
            "FROM document_chunks AS dc JOIN documents AS d ON dc.document_id = d.id "
            "WHERE (dc.content &@~ :query OR d.title &@~ :query OR dc.section_title &@~ :query) "
            "ORDER BY keyword_score DESC LIMIT :limit"
        )
        keyword_params = {"query": query, "limit": limit}
        try:
            keyword_rows = await _exec(keyword_sql, keyword_params)
        except Exception as e:
            logger.error(f"Cross-keyword search failed: {e}")
            keyword_rows = []

        def _rank_map(rows: List[Dict[str, Any]]) -> Dict[int, int]:
            rank = {}
            for i, r in enumerate(rows, start=1):
                rank[int(r["chunk_id"])] = i
            return rank

        dense_rank = _rank_map(dense_rows)
        sparse_rank = _rank_map(sparse_rows)
        keyword_rank = _rank_map(keyword_rows)

        all_keys = set(list(dense_rank.keys()) + list(sparse_rank.keys()) + list(keyword_rank.keys()))
        merged: List[tuple] = []
        for chunk_id in all_keys:
            payload = {}
            for src in (dense_rows, sparse_rows, keyword_rows):
                for row in src:
                    if int(row["chunk_id"]) == int(chunk_id):
                        payload = row
                        break
            merged.append((int(chunk_id), payload))

        results: List[SearchResult] = []
        now = datetime.utcnow()
        scored: List[Dict[str, Any]] = []
        for chunk_id, payload in merged:
            dense_score = None
            sparse_score = None
            keyword_score = None
            created_at = payload.get("created_at") if isinstance(payload, dict) else None
            if dense_rows:
                for r in dense_rows:
                    if int(r["chunk_id"]) == chunk_id:
                        dense_score = float(r.get("dense_score", 0.0))
                        break
            if sparse_rows:
                for r in sparse_rows:
                    if int(r["chunk_id"]) == chunk_id:
                        sparse_score = float(r.get("sparse_score", 0.0))
                        break
            if keyword_rows:
                for r in keyword_rows:
                    if int(r["chunk_id"]) == chunk_id:
                        keyword_score = float(r.get("keyword_score", 0.0))
                        break
            dense_score = 0.0 if dense_score is None else dense_score
            sparse_score = 0.0 if sparse_score is None else sparse_score
            keyword_score = 0.0 if keyword_score is None else keyword_score
            recency = 0.0
            if created_at:
                try:
                    created = created_at if isinstance(created_at, datetime) else datetime.fromisoformat(str(created_at))
                    days = (now - created).days
                    recency = math.exp(-days / 365.0)
                except Exception:
                    recency = 0.0
            dense_rrf = 1.0 / (dense_rank.get(chunk_id, 999999) + 60) if dense_score is not None else 0.0
            sparse_rrf = 1.0 / (sparse_rank.get(chunk_id, 999999) + 60) if sparse_score is not None else 0.0
            keyword_rrf = 1.0 / (keyword_rank.get(chunk_id, 999999) + 60) if keyword_score is not None else 0.0
            final_rrf = 0.5 * dense_rrf + 0.3 * sparse_rrf + 0.2 * keyword_rrf
            scored.append({
                "chunk_id": chunk_id,
                "document_id": payload.get("document_id") or 0,
                "document_title": payload.get("document_title") or "",
                "section_title": payload.get("section_title"),
                "content": payload.get("content") or "",
                "customer_id": payload.get("customer_id") or 0,
                "created_at": created_at,
                "final_rrf": final_rrf,
                "dense_score": dense_score or 0.0,
                "sparse_score": sparse_score or 0.0,
                "keyword_score": keyword_score or 0.0,
                "recency": recency,
            })
        if scored:
            min_fs = min(item["final_rrf"] for item in scored)
            max_fs = max(item["final_rrf"] for item in scored)
            range_fs = max_fs - min_fs
            for item in scored:
                norm = 0.0 if range_fs == 0 else (item["final_rrf"] - min_fs) / range_fs
                snippet = (item["content"][:200] + "...") if len(item["content"]) > 200 else item["content"]
                results.append(
                    SearchResult(
                        chunk_id=item["chunk_id"],
                        document_id=item["document_id"] or 0,
                        document_title=item["document_title"] or "",
                        section_title=item["section_title"],
                        content=item["content"],
                        customer_id=item["customer_id"],
                        score=float(norm),
                        scores=SearchScores(
                            dense=float(item["dense_score"] or 0.0),
                            sparse=float(item["sparse_score"] or 0.0),
                            keyword=float(item["keyword_score"] or 0.0),
                            recency=float(item["recency"] or 0.0),
                        ),
                        snippet=snippet,
                    )
                )
        results.sort(key=lambda r: (r.score, r.document_title), reverse=True)
        if len(results) > limit:
            results = results[:limit]
        return results
