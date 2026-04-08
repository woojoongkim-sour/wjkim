from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from enum import Enum


class SourceType(str, Enum):
    DOCUMENT = "document"
    REFINED_DOCUMENT = "refined_document"
    EVENT = "event"
    INCIDENT = "incident"
    SANITIZED_KNOWLEDGE = "sanitized_knowledge"
    METADATA = "metadata"


class LimitationFlag(str, Enum):
    PROTECTED_DOCUMENT = "protected_document"
    NO_REFINED_CONTENT = "no_refined_content"
    METADATA_ONLY = "metadata_only"
    EXTERNAL_CONTENT_UNAVAILABLE = "external_content_unavailable"


class Citation(BaseModel):
    source_id: str
    source_type: SourceType
    title: str
    content_preview: str
    relevance_score: float = Field(ge=0.0, le=1.0)


class Evidence(BaseModel):
    id: int
    type: SourceType
    title: str
    content_preview: Optional[str] = None
    matched_by: str
    limitation: Optional[str] = None


class ChatMessageInput(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    query: str
    customer_id: int
    context_ids: Optional[List[int]] = None
    use_sanitized_knowledge: bool = True
    conversation_history: Optional[List[ChatMessageInput]] = None


class ChatResponse(BaseModel):
    answer: str
    evidence: List[Evidence]
    source_representation: str
    limitation_notice: Optional[str] = None
    limitation_flags: List[LimitationFlag] = []
    requires_manual_confirmation: bool = False
    conversation_id: Optional[str] = None


class EnrichRequest(BaseModel):
    occurrence_id: int
    customer_id: int
    include_sanitized: bool = True


class EnrichEvidence(BaseModel):
    id: int
    type: str
    title: str
    content_available: bool
    limitation: Optional[str] = None


class EnrichResponse(BaseModel):
    occurrence_id: int
    event_summary: str
    related_documents: List[EnrichEvidence]
    related_incidents: List[dict]
    recommended_actions: List[str]
    metric_log_evidence: List[dict]
    limitation_flags: List[LimitationFlag]
