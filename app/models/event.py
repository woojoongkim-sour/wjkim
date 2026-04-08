from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
from app.models.enums import EventSeverity, EventStatus


class EventOccurrence(Base):
    __tablename__ = "event_occurrences"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False, index=True)
    
    source_system = Column(String(100), nullable=False, index=True)
    source_event_id = Column(String(255), nullable=False, index=True)
    
    event_name = Column(String(500), nullable=False)
    severity = Column(SQLEnum(EventSeverity), default=EventSeverity.MEDIUM)
    
    host = Column(String(255), index=True)
    service = Column(String(255), index=True)
    
    first_seen_at = Column(DateTime(timezone=True), nullable=False)
    last_seen_at = Column(DateTime(timezone=True))
    current_status = Column(SQLEnum(EventStatus), default=EventStatus.OPEN, index=True)
    
    occurrence_count = Column(Integer, default=1)
    raw_payload_reference = Column(Text)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    customer = relationship("Customer", back_populates="event_occurrences")
    state_history = relationship("EventStateHistory", back_populates="occurrence")
    handling_records = relationship("EventHandlingRecord", back_populates="occurrence")
    assessment = relationship("EventAssessment", back_populates="occurrence", uselist=False)
    metric_log_evidence = relationship("MetricLogEvidence", back_populates="occurrence")


class EventStateHistory(Base):
    __tablename__ = "event_state_history"

    id = Column(Integer, primary_key=True, index=True)
    occurrence_id = Column(Integer, ForeignKey("event_occurrences.id"), nullable=False, index=True)
    
    previous_state = Column(SQLEnum(EventStatus))
    new_state = Column(SQLEnum(EventStatus), nullable=False)
    
    changed_by = Column(String(255))
    source = Column(String(100))
    description = Column(Text)
    
    changed_at = Column(DateTime(timezone=True), nullable=False)

    occurrence = relationship("EventOccurrence", back_populates="state_history")


class EventHandlingRecord(Base):
    __tablename__ = "event_handling_records"

    id = Column(Integer, primary_key=True, index=True)
    occurrence_id = Column(Integer, ForeignKey("event_occurrences.id"), nullable=False, index=True)
    
    action_type = Column(String(100), nullable=False)
    action_summary = Column(Text, nullable=False)
    action_details = Column(Text)
    
    actor = Column(String(255), nullable=False)
    executed_at = Column(DateTime(timezone=True), nullable=False)
    
    related_ticket = Column(String(255))
    result_status = Column(String(50))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    occurrence = relationship("EventOccurrence", back_populates="handling_records")


class EventAssessment(Base):
    __tablename__ = "event_assessments"

    id = Column(Integer, primary_key=True, index=True)
    occurrence_id = Column(Integer, ForeignKey("event_occurrences.id"), nullable=False, index=True)
    
    recurrence_score = Column(Integer)
    risk_score = Column(Integer)
    pattern_summary = Column(Text)
    probable_cause = Column(Text)
    
    transfer_to_incident = Column(Boolean, default=False)
    analyzed_at = Column(DateTime(timezone=True))
    analyzer_type = Column(String(50))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    occurrence = relationship("EventOccurrence", back_populates="assessment")


class MetricLogEvidence(Base):
    __tablename__ = "metric_log_evidence"

    id = Column(Integer, primary_key=True, index=True)
    occurrence_id = Column(Integer, ForeignKey("event_occurrences.id"), nullable=False, index=True)
    
    evidence_type = Column(String(50), nullable=False)
    source = Column(String(100), nullable=False)
    
    summary = Column(Text, nullable=False)
    snapshot_reference = Column(Text)
    query_params_json = Column(Text)
    
    collected_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    occurrence = relationship("EventOccurrence", back_populates="metric_log_evidence")


class IncidentCase(Base):
    __tablename__ = "incident_cases"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False, index=True)
    
    title = Column(String(500), nullable=False)
    description = Column(Text)
    
    severity = Column(SQLEnum(EventSeverity))
    impact_scope = Column(Text)
    
    cause_summary = Column(Text)
    resolution_summary = Column(Text)
    
    occurred_at = Column(DateTime(timezone=True))
    resolved_at = Column(DateTime(timezone=True))
    
    related_event_ids = Column(Text)
    related_document_ids = Column(Text)
    tags = Column(Text)
    
    can_be_sanitized = Column(Boolean, default=False)
    is_sanitized = Column(Boolean, default=False)
    
    created_by = Column(String(255))
    updated_by = Column(String(255))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    customer = relationship("Customer", back_populates="incident_cases")
    documents = relationship("Document", secondary="incident_case_document_association")
