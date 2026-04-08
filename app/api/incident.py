import logging
from datetime import datetime, timedelta
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, case
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.event import (
    EventOccurrence, EventStateHistory, EventHandlingRecord,
    EventAssessment, MetricLogEvidence, IncidentCase,
)
from app.models.document import Document
from app.models.enums import EventSeverity, EventStatus
from app.schemas.incident import (
    ZabbixWebhookPayload, WebhookResponse,
    DashboardResponse, SeverityCount, StatusCount, TopRiskEvent, RecentActivity,
    EventListItem, EventListResponse,
    EventDetailResponse, StateHistoryItem, HandlingRecordItem, AssessmentDetail,
    MetricLogEvidenceItem, RelatedDocumentBrief, RelatedIncidentBrief,
    AnalysisReportResponse,
    EventChatRequest, EventChatResponse,
)
from app.services.zabbix_service import ZabbixWebhookService
from app.services.analysis_service import AnalysisService
from app.services.event_chat_service import EventChatService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/incident", tags=["incident"])


@router.post("/webhook/zabbix", response_model=WebhookResponse)
async def receive_zabbix_webhook(
    payload: ZabbixWebhookPayload,
    customer_id: int = Query(..., description="Customer ID for this monitoring source"),
    db: AsyncSession = Depends(get_db),
):
    service = ZabbixWebhookService(db)
    return await service.process_webhook(payload, customer_id)


@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard(
    customer_id: int,
    db: AsyncSession = Depends(get_db),
):
    base_filter = EventOccurrence.customer_id == customer_id

    total_result = await db.execute(
        select(func.count(EventOccurrence.id)).where(base_filter)
    )
    total_events = total_result.scalar() or 0

    open_result = await db.execute(
        select(func.count(EventOccurrence.id)).where(
            base_filter,
            EventOccurrence.current_status.in_([EventStatus.OPEN, EventStatus.ACKNOWLEDGED, EventStatus.REOPENED]),
        )
    )
    open_events = open_result.scalar() or 0

    critical_result = await db.execute(
        select(func.count(EventOccurrence.id)).where(
            base_filter,
            EventOccurrence.severity == EventSeverity.CRITICAL,
            EventOccurrence.current_status.in_([EventStatus.OPEN, EventStatus.ACKNOWLEDGED, EventStatus.REOPENED]),
        )
    )
    critical_events = critical_result.scalar() or 0

    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    resolved_result = await db.execute(
        select(func.count(EventOccurrence.id)).where(
            base_filter,
            EventOccurrence.current_status == EventStatus.RESOLVED,
            EventOccurrence.updated_at >= today_start,
        )
    )
    resolved_today = resolved_result.scalar() or 0

    severity_result = await db.execute(
        select(EventOccurrence.severity, func.count(EventOccurrence.id))
        .where(base_filter)
        .group_by(EventOccurrence.severity)
    )
    severity_distribution = [
        SeverityCount(severity=str(row[0]), count=row[1])
        for row in severity_result.all()
    ]

    status_result = await db.execute(
        select(EventOccurrence.current_status, func.count(EventOccurrence.id))
        .where(base_filter)
        .group_by(EventOccurrence.current_status)
    )
    status_distribution = [
        StatusCount(status=str(row[0]), count=row[1])
        for row in status_result.all()
    ]

    top_risk_result = await db.execute(
        select(EventOccurrence)
        .outerjoin(EventAssessment)
        .where(
            base_filter,
            EventOccurrence.current_status.in_([EventStatus.OPEN, EventStatus.ACKNOWLEDGED, EventStatus.REOPENED]),
        )
        .order_by(
            EventAssessment.risk_score.desc().nullslast(),
            EventOccurrence.occurrence_count.desc(),
        )
        .limit(10)
    )
    top_risk_events = []
    for event in top_risk_result.scalars().all():
        assessment_result = await db.execute(
            select(EventAssessment).where(EventAssessment.occurrence_id == event.id)
        )
        assessment = assessment_result.scalar_one_or_none()
        top_risk_events.append(TopRiskEvent(
            id=event.id,
            event_name=event.event_name,
            severity=str(event.severity),
            host=event.host,
            occurrence_count=event.occurrence_count,
            risk_score=assessment.risk_score if assessment else None,
            current_status=str(event.current_status),
            first_seen_at=event.first_seen_at,
        ))

    recent_handling_result = await db.execute(
        select(EventHandlingRecord, EventOccurrence)
        .join(EventOccurrence, EventHandlingRecord.occurrence_id == EventOccurrence.id)
        .where(EventOccurrence.customer_id == customer_id)
        .order_by(EventHandlingRecord.executed_at.desc())
        .limit(10)
    )
    recent_activities = [
        RecentActivity(
            id=hr.id,
            event_name=event.event_name,
            action=hr.action_summary,
            actor=hr.actor,
            timestamp=hr.executed_at,
        )
        for hr, event in recent_handling_result.all()
    ]

    recurring_result = await db.execute(
        select(func.count(EventOccurrence.id)).where(
            base_filter,
            EventOccurrence.occurrence_count > 3,
        )
    )
    recurring_event_count = recurring_result.scalar() or 0

    return DashboardResponse(
        total_events=total_events,
        open_events=open_events,
        critical_events=critical_events,
        resolved_today=resolved_today,
        severity_distribution=severity_distribution,
        status_distribution=status_distribution,
        top_risk_events=top_risk_events,
        recent_activities=recent_activities,
        recurring_event_count=recurring_event_count,
    )


@router.get("/events", response_model=EventListResponse)
async def list_events(
    customer_id: int,
    current_status: Optional[str] = None,
    severity: Optional[str] = None,
    host: Optional[str] = None,
    service: Optional[str] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, le=200),
    sort_by: str = Query("last_seen_at", regex="^(last_seen_at|first_seen_at|severity|occurrence_count)$"),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
    db: AsyncSession = Depends(get_db),
):
    base_query = select(EventOccurrence).where(
        EventOccurrence.customer_id == customer_id
    )

    if current_status:
        base_query = base_query.where(EventOccurrence.current_status == current_status)
    if severity:
        base_query = base_query.where(EventOccurrence.severity == severity)
    if host:
        base_query = base_query.where(EventOccurrence.host.ilike(f"%{host}%"))
    if service:
        base_query = base_query.where(EventOccurrence.service == service)
    if search:
        base_query = base_query.where(EventOccurrence.event_name.ilike(f"%{search}%"))

    count_result = await db.execute(
        select(func.count()).select_from(base_query.subquery())
    )
    total = count_result.scalar() or 0

    sort_column = getattr(EventOccurrence, sort_by)
    if sort_order == "desc":
        base_query = base_query.order_by(sort_column.desc())
    else:
        base_query = base_query.order_by(sort_column.asc())

    offset = (page - 1) * page_size
    base_query = base_query.offset(offset).limit(page_size)

    result = await db.execute(base_query)
    events = result.scalars().all()

    event_items = []
    for event in events:
        assessment_result = await db.execute(
            select(EventAssessment).where(EventAssessment.occurrence_id == event.id)
        )
        assessment = assessment_result.scalar_one_or_none()

        event_items.append(EventListItem(
            id=event.id,
            event_name=event.event_name,
            severity=str(event.severity),
            host=event.host,
            service=event.service if isinstance(event.service, str) else None,
            current_status=str(event.current_status),
            first_seen_at=event.first_seen_at,
            last_seen_at=event.last_seen_at,
            occurrence_count=event.occurrence_count,
            source_system=event.source_system,
            has_assessment=assessment is not None,
            has_related_docs=False,
            risk_score=assessment.risk_score if assessment else None,
            recurrence_score=assessment.recurrence_score if assessment else None,
        ))

    return EventListResponse(
        events=event_items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/events/{event_id}", response_model=EventDetailResponse)
async def get_event_detail(
    event_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(EventOccurrence)
        .options(
            selectinload(EventOccurrence.state_history),
            selectinload(EventOccurrence.handling_records),
            selectinload(EventOccurrence.assessment),
            selectinload(EventOccurrence.metric_log_evidence),
        )
        .where(EventOccurrence.id == event_id)
    )
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    from sqlalchemy import or_
    keywords = [kw for kw in event.event_name.split() if len(kw) > 2][:3]
    related_docs = []
    limitation_flags = []

    if keywords:
        keyword_filters = []
        for kw in keywords:
            keyword_filters.append(Document.title.ilike(f"%{kw}%"))
            keyword_filters.append(Document.tags.ilike(f"%{kw}%"))

        doc_result = await db.execute(
            select(Document).where(
                Document.customer_id == event.customer_id,
                Document.is_active == True,
                or_(*keyword_filters),
            ).limit(10)
        )

        for doc in doc_result.scalars().all():
            content_available = doc.processing_capability in [
                "fulltext_extractable", "chunkable", "embeddable"
            ]
            is_refined = doc.is_refined

            limitation = None
            if doc.protection_type != "none" and not is_refined:
                limitation = f"Protected by {doc.protection_type}"
                limitation_flags.append(limitation)

            related_docs.append(RelatedDocumentBrief(
                id=doc.id,
                title=doc.title,
                document_type=doc.document_type,
                protection_type=doc.protection_type,
                content_available=content_available or is_refined,
                refined_available=is_refined,
                limitation=limitation,
            ))

    incident_result = await db.execute(
        select(IncidentCase).where(
            IncidentCase.customer_id == event.customer_id,
        ).limit(5)
    )
    related_incidents = [
        RelatedIncidentBrief(
            id=inc.id,
            title=inc.title,
            severity=str(inc.severity) if inc.severity else None,
            occurred_at=inc.occurred_at,
            resolution_summary=inc.resolution_summary,
        )
        for inc in incident_result.scalars().all()
    ]

    recommended_actions = [
        "서버 상태 확인",
        "최근 변경사항 검토",
        "관련 서비스 의존성 점검",
        "모니터링 임계값 확인",
    ]

    return EventDetailResponse(
        id=event.id,
        event_name=event.event_name,
        severity=str(event.severity),
        host=event.host,
        service=event.service if isinstance(event.service, str) else None,
        current_status=str(event.current_status),
        source_system=event.source_system,
        source_event_id=event.source_event_id,
        first_seen_at=event.first_seen_at,
        last_seen_at=event.last_seen_at,
        occurrence_count=event.occurrence_count,
        raw_payload_reference=event.raw_payload_reference,
        created_at=event.created_at,
        state_history=[
            StateHistoryItem(
                id=sh.id,
                previous_state=str(sh.previous_state) if sh.previous_state else None,
                new_state=str(sh.new_state),
                changed_by=sh.changed_by,
                source=sh.source,
                description=sh.description,
                changed_at=sh.changed_at,
            )
            for sh in sorted(event.state_history, key=lambda x: x.changed_at, reverse=True)
        ],
        handling_records=[
            HandlingRecordItem(
                id=hr.id,
                action_type=hr.action_type,
                action_summary=hr.action_summary,
                action_details=hr.action_details,
                actor=hr.actor,
                executed_at=hr.executed_at,
                related_ticket=hr.related_ticket,
                result_status=hr.result_status,
            )
            for hr in sorted(event.handling_records, key=lambda x: x.executed_at, reverse=True)
        ],
        assessment=AssessmentDetail(
            id=event.assessment.id,
            recurrence_score=event.assessment.recurrence_score,
            risk_score=event.assessment.risk_score,
            pattern_summary=event.assessment.pattern_summary,
            probable_cause=event.assessment.probable_cause,
            transfer_to_incident=event.assessment.transfer_to_incident,
            analyzed_at=event.assessment.analyzed_at,
            analyzer_type=event.assessment.analyzer_type,
        ) if event.assessment else None,
        metric_log_evidence=[
            MetricLogEvidenceItem(
                id=ev.id,
                evidence_type=ev.evidence_type,
                source=ev.source,
                summary=ev.summary,
                collected_at=ev.collected_at,
            )
            for ev in event.metric_log_evidence
        ],
        related_documents=related_docs,
        related_incidents=related_incidents,
        recommended_actions=recommended_actions,
        limitation_flags=limitation_flags,
    )


@router.get("/events/{event_id}/analysis", response_model=AnalysisReportResponse)
async def get_analysis_report(
    event_id: int,
    db: AsyncSession = Depends(get_db),
):
    service = AnalysisService(db)
    try:
        return await service.generate_analysis_report(event_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/events/{event_id}/chat", response_model=EventChatResponse)
async def event_context_chat(
    event_id: int,
    request: EventChatRequest,
    db: AsyncSession = Depends(get_db),
):
    service = EventChatService(db)
    return await service.chat(event_id, request)


@router.post("/events/{event_id}/acknowledge")
async def acknowledge_event(
    event_id: int,
    actor: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(EventOccurrence).where(EventOccurrence.id == event_id)
    )
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    previous = event.current_status
    event.current_status = EventStatus.ACKNOWLEDGED

    state_history = EventStateHistory(
        occurrence_id=event_id,
        previous_state=previous,
        new_state=EventStatus.ACKNOWLEDGED,
        changed_by=actor,
        source="incident_ui",
        description="Event acknowledged by operator",
        changed_at=datetime.utcnow(),
    )
    db.add(state_history)
    await db.commit()

    return {"status": "ok", "message": "Event acknowledged", "event_id": event_id}


@router.post("/events/{event_id}/resolve")
async def resolve_event(
    event_id: int,
    actor: str = Query(...),
    resolution_note: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(EventOccurrence).where(EventOccurrence.id == event_id)
    )
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    previous = event.current_status
    event.current_status = EventStatus.RESOLVED

    state_history = EventStateHistory(
        occurrence_id=event_id,
        previous_state=previous,
        new_state=EventStatus.RESOLVED,
        changed_by=actor,
        source="incident_ui",
        description=resolution_note or "Event resolved by operator",
        changed_at=datetime.utcnow(),
    )
    db.add(state_history)

    if resolution_note:
        handling = EventHandlingRecord(
            occurrence_id=event_id,
            action_type="resolve",
            action_summary=resolution_note,
            actor=actor,
            executed_at=datetime.utcnow(),
            result_status="resolved",
        )
        db.add(handling)

    await db.commit()

    return {"status": "ok", "message": "Event resolved", "event_id": event_id}
