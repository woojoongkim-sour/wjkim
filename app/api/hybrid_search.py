from fastapi import APIRouter, Depends, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.core.database import get_db
from app.services.hybrid_search import HybridSearchService
from app.services.agentic_rag import AdaptiveRAGOrchestrator
from app.schemas.search import (
    HybridSearchRequest, HybridSearchResponse,
    VersionSearchRequest, CrossSearchRequest
)

router = APIRouter(prefix="/search", tags=["Search"])


@router.post("/hybrid", response_model=HybridSearchResponse)
async def hybrid_search(
    request: HybridSearchRequest,
    db: AsyncSession = Depends(get_db),
):
    """Execute 3-way hybrid search (Dense + Sparse + Keyword with RRF fusion)."""
    service = HybridSearchService(db)
    return await service.search(request)


@router.post("/version", response_model=HybridSearchResponse)
async def version_search(
    request: VersionSearchRequest,
    db: AsyncSession = Depends(get_db),
):
    """Execute time-based version search."""
    service = HybridSearchService(db)
    return await service.version_search(request)


@router.post("/cross", response_model=HybridSearchResponse)
async def cross_search(
    request: CrossSearchRequest,
    db: AsyncSession = Depends(get_db),
):
    """Search across all customers for similar cases."""
    service = HybridSearchService(db)
    return await service.cross_search(request)


@router.post("/rag")
async def adaptive_rag(
    query: str,
    customer_id: int,
    cross_search: bool = False,
    db: AsyncSession = Depends(get_db),
):
    """Execute adaptive RAG with complexity-based routing."""
    orchestrator = AdaptiveRAGOrchestrator(db)
    return await orchestrator.process(query, customer_id, cross_search)


@router.get("/health")
async def search_health(
    db: AsyncSession = Depends(get_db)
):
    """Check search service health."""
    try:
        from sqlalchemy import text
        await db.execute(text("SELECT 1"))
        return {"status": "healthy", "embedding_service": "unknown"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
