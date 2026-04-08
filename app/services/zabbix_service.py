import logging
from datetime import datetime
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.sql import func

from app.models.event import EventOccurrence, EventStateHistory
from app.models.enums import EventSeverity, EventStatus
from app.schemas.incident import ZabbixWebhookPayload, WebhookResponse

logger = logging.getLogger(__name__)

ZABBIX_SEVERITY_MAP = {
    "Disaster": EventSeverity.CRITICAL,
    "High": EventSeverity.HIGH,
    "Average": EventSeverity.MEDIUM,
    "Warning": EventSeverity.LOW,
    "Information": EventSeverity.INFO,
    "Not classified": EventSeverity.INFO,
}


class ZabbixWebhookService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def process_webhook(
        self, payload: ZabbixWebhookPayload, customer_id: int
    ) -> WebhookResponse:
        severity = ZABBIX_SEVERITY_MAP.get(payload.trigger_severity, EventSeverity.MEDIUM)

        is_resolved = (
            payload.trigger_status == "RESOLVED" or payload.event_value == "0"
        )

        event_time = self._parse_zabbix_datetime(payload.event_date, payload.event_time)

        existing = await self._find_existing_occurrence(
            customer_id=customer_id,
            source_event_id=payload.event_id,
        )

        if existing:
            return await self._update_existing(existing, payload, severity, is_resolved, event_time)

        return await self._create_new(payload, customer_id, severity, is_resolved, event_time)

    async def _find_existing_occurrence(
        self, customer_id: int, source_event_id: str
    ) -> Optional[EventOccurrence]:
        result = await self.db.execute(
            select(EventOccurrence).where(
                EventOccurrence.customer_id == customer_id,
                EventOccurrence.source_system == "zabbix",
                EventOccurrence.source_event_id == source_event_id,
            )
        )
        return result.scalar_one_or_none()

    async def _create_new(
        self,
        payload: ZabbixWebhookPayload,
        customer_id: int,
        severity: EventSeverity,
        is_resolved: bool,
        event_time: datetime,
    ) -> WebhookResponse:
        status = EventStatus.RESOLVED if is_resolved else EventStatus.OPEN

        occurrence = EventOccurrence(
            customer_id=customer_id,
            source_system="zabbix",
            source_event_id=payload.event_id,
            event_name=payload.trigger_name,
            severity=severity,
            host=payload.host_name,
            first_seen_at=event_time,
            last_seen_at=event_time,
            current_status=status,
            occurrence_count=1,
            raw_payload_reference=payload.model_dump_json(),
        )

        self.db.add(occurrence)
        await self.db.commit()
        await self.db.refresh(occurrence)

        state_history = EventStateHistory(
            occurrence_id=occurrence.id,
            previous_state=None,
            new_state=status,
            changed_by="zabbix_webhook",
            source="zabbix",
            description=f"Initial event from Zabbix: {payload.trigger_name}",
            changed_at=event_time,
        )
        self.db.add(state_history)
        await self.db.commit()

        return WebhookResponse(
            status="ok",
            occurrence_id=occurrence.id,
            action="created",
            message=f"New event occurrence created: {payload.trigger_name}",
        )

    async def _update_existing(
        self,
        existing: EventOccurrence,
        payload: ZabbixWebhookPayload,
        severity: EventSeverity,
        is_resolved: bool,
        event_time: datetime,
    ) -> WebhookResponse:
        previous_status = existing.current_status

        if is_resolved:
            new_status = EventStatus.RESOLVED
            action = "resolved"
        else:
            existing.occurrence_count += 1
            new_status = EventStatus.REOPENED if previous_status == EventStatus.RESOLVED else existing.current_status
            action = "updated"

        existing.last_seen_at = event_time
        existing.current_status = new_status
        existing.severity = severity

        if previous_status != new_status:
            state_history = EventStateHistory(
                occurrence_id=existing.id,
                previous_state=previous_status,
                new_state=new_status,
                changed_by="zabbix_webhook",
                source="zabbix",
                description=f"Status changed via Zabbix webhook",
                changed_at=event_time,
            )
            self.db.add(state_history)

        await self.db.commit()
        await self.db.refresh(existing)

        return WebhookResponse(
            status="ok",
            occurrence_id=existing.id,
            action=action,
            message=f"Event {action}: {payload.trigger_name}",
        )

    def _parse_zabbix_datetime(
        self, date_str: Optional[str], time_str: Optional[str]
    ) -> datetime:
        if date_str and time_str:
            try:
                return datetime.strptime(f"{date_str} {time_str}", "%Y.%m.%d %H:%M:%S")
            except ValueError:
                pass

        if date_str:
            try:
                return datetime.strptime(date_str, "%Y.%m.%d")
            except ValueError:
                pass

        return datetime.utcnow()
