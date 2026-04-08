from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from typing import List, Optional

from app.core.database import get_db
from app.models.event import EventOccurrence, EventStateHistory, EventHandlingRecord, EventAssessment
from app.schemas.event import (
    EventOccurrenceCreate, EventOccurrenceUpdate, EventOccurrenceResponse,
    EventStateHistoryResponse, EventHandlingRecordResponse, EventAssessmentResponse
)

router = APIRouter()


@router.post("", response_model=EventOccurrenceResponse)
async def create_event(
    event: EventOccurrenceCreate,
    db: AsyncSession = Depends(get_db)
):
    existing = await db.execute(
        select(EventOccurrence).where(
            EventOccurrence.source_system == event.source_system,
            EventOccurrence.source_event_id == event.source_event_id,
            EventOccurrence.customer_id == event.customer_id
        )
    )
    existing_event = existing.scalar_one_or_none()
    
    if existing_event:
        existing_event.last_seen_at = event.first_seen_at
        existing_event.occurrence_count += 1
        await db.commit()
        await db.refresh(existing_event)
        return existing_event
    
    db_event = EventOccurrence(**event.model_dump())
    db.add(db_event)
    await db.commit()
    await db.refresh(db_event)
    return db_event


@router.get("", response_model=List[EventOccurrenceResponse])
async def list_events(
    customer_id: int,
    current_status: Optional[str] = None,
    severity: Optional[str] = None,
    host: Optional[str] = None,
    service: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, le=500),
    db: AsyncSession = Depends(get_db)
):
    query = select(EventOccurrence)
    query = query.where(EventOccurrence.customer_id == customer_id)
    
    if current_status:
        query = query.where(EventOccurrence.current_status == current_status)
    if severity:
        query = query.where(EventOccurrence.severity == severity)
    if host:
        query = query.where(EventOccurrence.host == host)
    if service:
        query = query.where(EventOccurrence.service == service)
    
    query = query.offset(skip).limit(limit).order_by(EventOccurrence.last_seen_at.desc())
    
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{event_id}", response_model=EventOccurrenceResponse)
async def get_event(
    event_id: int,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(EventOccurrence)
        .options(
            selectinload(EventOccurrence.state_history),
            selectinload(EventOccurrence.handling_records),
            selectinload(EventOccurrence.assessment)
        )
        .where(EventOccurrence.id == event_id)
    )
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


@router.patch("/{event_id}", response_model=EventOccurrenceResponse)
async def update_event(
    event_id: int,
    event_update: EventOccurrenceUpdate,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(EventOccurrence).where(EventOccurrence.id == event_id))
    db_event = result.scalar_one_or_none()
    if not db_event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    update_data = event_update.model_dump(exclude_unset=True)
    
    if "current_status" in update_data and update_data["current_status"]:
        state_history = EventStateHistory(
            occurrence_id=event_id,
            previous_state=db_event.current_status,
            new_state=update_data["current_status"],
            changed_at=func.now()
        )
        db.add(state_history)
    
    for key, value in update_data.items():
        setattr(db_event, key, value)
    
    await db.commit()
    await db.refresh(db_event)
    return db_event


@router.post("/{event_id}/handling", response_model=EventHandlingRecordResponse)
async def add_handling_record(
    event_id: int,
    action_type: str,
    action_summary: str,
    actor: str,
    action_details: Optional[str] = None,
    related_ticket: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(EventOccurrence).where(EventOccurrence.id == event_id))
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    record = EventHandlingRecord(
        occurrence_id=event_id,
        action_type=action_type,
        action_summary=action_summary,
        action_details=action_details,
        actor=actor,
        executed_at=func.now(),
        related_ticket=related_ticket
    )
    
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


@router.get("/{event_id}/history", response_model=List[EventStateHistoryResponse])
async def get_event_history(
    event_id: int,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(EventStateHistory)
        .where(EventStateHistory.occurrence_id == event_id)
        .order_by(EventStateHistory.changed_at.desc())
    )
    return result.scalars().all()


@router.get("/{event_id}/handling", response_model=List[EventHandlingRecordResponse])
async def get_handling_records(
    event_id: int,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(EventHandlingRecord)
        .where(EventHandlingRecord.occurrence_id == event_id)
        .order_by(EventHandlingRecord.executed_at.desc())
    )
    return result.scalars().all()


@router.get("/{event_id}/assessment", response_model=Optional[EventAssessmentResponse])
async def get_event_assessment(
    event_id: int,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(EventAssessment).where(EventAssessment.occurrence_id == event_id)
    )
    return result.scalar_one_or_none()
