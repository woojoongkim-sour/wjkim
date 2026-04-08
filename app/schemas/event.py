from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from app.models.enums import EventSeverity, EventStatus


class EventOccurrenceBase(BaseModel):
    event_name: str = Field(..., max_length=500)
    severity: EventSeverity = EventSeverity.MEDIUM
    host: Optional[str] = None
    service: Optional[str] = None


class EventOccurrenceCreate(EventOccurrenceBase):
    customer_id: int
    source_system: str
    source_event_id: str
    first_seen_at: datetime
    raw_payload_reference: Optional[str] = None


class EventOccurrenceUpdate(BaseModel):
    current_status: Optional[EventStatus] = None
    severity: Optional[EventSeverity] = None
    last_seen_at: Optional[datetime] = None


class EventOccurrenceResponse(EventOccurrenceBase):
    id: int
    customer_id: int
    source_system: str
    source_event_id: str
    first_seen_at: datetime
    last_seen_at: Optional[datetime]
    current_status: EventStatus
    occurrence_count: int
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


class EventStateHistoryResponse(BaseModel):
    id: int
    previous_state: Optional[EventStatus]
    new_state: EventStatus
    changed_by: Optional[str]
    source: Optional[str]
    description: Optional[str]
    changed_at: datetime

    model_config = {"from_attributes": True}


class EventHandlingRecordResponse(BaseModel):
    id: int
    action_type: str
    action_summary: str
    action_details: Optional[str]
    actor: str
    executed_at: datetime
    related_ticket: Optional[str]
    result_status: Optional[str]

    model_config = {"from_attributes": True}


class EventAssessmentResponse(BaseModel):
    id: int
    recurrence_score: Optional[int]
    risk_score: Optional[int]
    pattern_summary: Optional[str]
    probable_cause: Optional[str]
    transfer_to_incident: bool
    analyzed_at: Optional[datetime]
    analyzer_type: Optional[str]

    model_config = {"from_attributes": True}


class EventEnrichmentRequest(BaseModel):
    occurrence_id: int
    customer_id: int


class EventEnrichmentResponse(BaseModel):
    occurrence_id: int
    event_summary: str
    related_documents: List[dict]
    related_incidents: List[dict]
    recommended_actions: List[str]
    metric_log_evidence: List[dict]
    limitation_flags: List[str]
