from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime
from app.models.enums import AuditAction


class AuditLogResponse(BaseModel):
    id: int
    customer_id: Optional[int]
    user_id: Optional[str]
    user_email: Optional[str]
    action: str
    resource_type: Optional[str]
    resource_id: Optional[str]
    request_path: Optional[str]
    response_status_code: Optional[int]
    ip_address: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    query: str
    customer_id: int
    context_ids: Optional[List[int]] = None
    use_sanitized_knowledge: bool = True
    conversation_history: Optional[List[ChatMessage]] = None


class ChatResponse(BaseModel):
    answer: str
    evidence: List[dict]
    source_representation: str
    limitation_notice: Optional[str]
    requires_manual_confirmation: bool
    conversation_id: Optional[str] = None


class SearchRequest(BaseModel):
    query: str
    customer_id: int
    filters: Optional[dict] = None
    search_modes: Optional[List[str]] = None
    limit: int = 20
    offset: int = 0


class SearchResponse(BaseModel):
    results: List[dict]
    total: int
    limitation_notices: List[str]


class GraphNode(BaseModel):
    id: str
    type: str
    label: str
    properties: dict


class GraphEdge(BaseModel):
    source: str
    target: str
    type: str
    properties: dict


class GraphContextRequest(BaseModel):
    entity_id: str
    entity_type: str
    customer_id: int
    depth: int = 2


class GraphContextResponse(BaseModel):
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    source_types: List[str]
    confidence: dict
