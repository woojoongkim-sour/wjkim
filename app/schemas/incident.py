from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

from app.models.enums import EventSeverity, EventStatus


class ZabbixWebhookPayload(BaseModel):
    event_id: str
    trigger_id: Optional[str] = None
    trigger_name: str
    trigger_severity: str  # Zabbix API: "Disaster"|"High"|"Average"|"Warning"|"Information"
    trigger_status: str  # Zabbix API: "PROBLEM"|"RESOLVED"
    host_name: str
    host_ip: Optional[str] = None
    event_date: Optional[str] = None
    event_time: Optional[str] = None
    event_value: Optional[str] = None  # Zabbix API: "1"=problem, "0"=resolved
    item_name: Optional[str] = None
    item_value: Optional[str] = None
    event_tags: Optional[str] = None
    event_message: Optional[str] = None


class WebhookResponse(BaseModel):
    status: str
    occurrence_id: int
    action: str
    message: str


class SeverityCount(BaseModel):
    severity: str
    count: int


class StatusCount(BaseModel):
    status: str
    count: int


class TopRiskEvent(BaseModel):
    id: int
    event_name: str
    severity: str
    host: Optional[str]
    occurrence_count: int
    risk_score: Optional[int]
    current_status: str
    first_seen_at: datetime


class RecentActivity(BaseModel):
    id: int
    event_name: str
    action: str
    actor: Optional[str]
    timestamp: datetime


class DashboardResponse(BaseModel):
    total_events: int
    open_events: int
    critical_events: int
    resolved_today: int
    severity_distribution: List[SeverityCount]
    status_distribution: List[StatusCount]
    top_risk_events: List[TopRiskEvent]
    recent_activities: List[RecentActivity]
    recurring_event_count: int


class EventListItem(BaseModel):
    id: int
    event_name: str
    severity: str
    host: Optional[str]
    service: Optional[str]
    current_status: str
    first_seen_at: datetime
    last_seen_at: Optional[datetime]
    occurrence_count: int
    source_system: str
    has_assessment: bool
    has_related_docs: bool
    risk_score: Optional[int] = None
    recurrence_score: Optional[int] = None

    model_config = {"from_attributes": True}


class EventListResponse(BaseModel):
    events: List[EventListItem]
    total: int
    page: int
    page_size: int


class StateHistoryItem(BaseModel):
    id: int
    previous_state: Optional[str]
    new_state: str
    changed_by: Optional[str]
    source: Optional[str]
    description: Optional[str]
    changed_at: datetime

    model_config = {"from_attributes": True}


class HandlingRecordItem(BaseModel):
    id: int
    action_type: str
    action_summary: str
    action_details: Optional[str]
    actor: str
    executed_at: datetime
    related_ticket: Optional[str]
    result_status: Optional[str]

    model_config = {"from_attributes": True}


class AssessmentDetail(BaseModel):
    id: int
    recurrence_score: Optional[int]
    risk_score: Optional[int]
    pattern_summary: Optional[str]
    probable_cause: Optional[str]
    transfer_to_incident: bool
    analyzed_at: Optional[datetime]
    analyzer_type: Optional[str]

    model_config = {"from_attributes": True}


class RelatedDocumentBrief(BaseModel):
    id: int
    title: str
    document_type: Optional[str]
    protection_type: str
    content_available: bool
    refined_available: bool
    limitation: Optional[str] = None


class RelatedIncidentBrief(BaseModel):
    id: int
    title: str
    severity: Optional[str]
    occurred_at: Optional[datetime]
    resolution_summary: Optional[str]


class MetricLogEvidenceItem(BaseModel):
    id: int
    evidence_type: str
    source: str
    summary: str
    collected_at: datetime

    model_config = {"from_attributes": True}


class EventDetailResponse(BaseModel):
    id: int
    event_name: str
    severity: str
    host: Optional[str]
    service: Optional[str]
    current_status: str
    source_system: str
    source_event_id: str
    first_seen_at: datetime
    last_seen_at: Optional[datetime]
    occurrence_count: int
    raw_payload_reference: Optional[str]
    created_at: datetime
    state_history: List[StateHistoryItem]
    handling_records: List[HandlingRecordItem]
    assessment: Optional[AssessmentDetail]
    metric_log_evidence: List[MetricLogEvidenceItem]
    related_documents: List[RelatedDocumentBrief]
    related_incidents: List[RelatedIncidentBrief]
    recommended_actions: List[str]
    limitation_flags: List[str]


class AnalysisReportResponse(BaseModel):
    occurrence_id: int
    event_name: str
    generated_at: datetime
    analyzer_type: str
    summary: str
    probable_causes: List[str]
    risk_level: str
    risk_score: int = Field(ge=0, le=100)
    recurrence_analysis: str
    recurrence_score: int = Field(ge=0, le=100)
    recommended_actions: List[str]
    related_patterns: List[str]
    evidence_used: List[dict]
    limitation_flags: List[str]


class EventChatMessage(BaseModel):
    role: str
    content: str


class EventChatRequest(BaseModel):
    query: str
    conversation_history: Optional[List[EventChatMessage]] = None
    use_sanitized_knowledge: bool = True


class EventChatEvidence(BaseModel):
    source_id: str
    source_type: str
    title: str
    content_preview: Optional[str] = None
    relevance_score: float = Field(ge=0.0, le=1.0, default=0.5)


class EventChatResponse(BaseModel):
    answer: str
    evidence: List[EventChatEvidence]
    limitation_notice: Optional[str] = None
    limitation_flags: List[str] = []
    requires_manual_confirmation: bool = False
    conversation_id: Optional[str] = None
