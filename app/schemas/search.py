from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class HybridSearchRequest(BaseModel):
    query: str
    customer_id: int
    filters: Optional[Dict[str, Any]] = None
    include_all_versions: bool = False
    target_date: Optional[str] = None  # YYYY-MM-DD format for time-based search
    limit: int = 20
    offset: int = 0
    cross_search: bool = False  # Search across all customers


class HybridSearchResult(BaseModel):
    chunk_id: int
    document_id: int
    document_title: str
    section_title: Optional[str]
    content: str
    customer_id: int
    score: float
    dense_score: Optional[float] = None
    sparse_score: Optional[float] = None
    keyword_score: Optional[float] = None
    rank_dense: Optional[int] = None
    rank_sparse: Optional[int] = None
    rank_keyword: Optional[int] = None
    version: Optional[int] = None
    is_latest: bool = True
    created_at: Optional[datetime] = None


class HybridSearchResponse(BaseModel):
    results: List[HybridSearchResult]
    total: int
    query_time_ms: float
    search_mode: str  # single-pass | multi-step
    escalation_triggered: bool = False
    dense_threshold_met: bool = True


class VersionSearchRequest(BaseModel):
    query: str
    customer_id: int
    target_date: str  # YYYY-MM-DD
    limit: int = 20


class CrossSearchRequest(BaseModel):
    query: str
    exclude_customer_id: Optional[int] = None
    limit: int = 10
