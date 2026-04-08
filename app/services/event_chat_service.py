from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Optional, List, Tuple

from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.models.event import (
    EventOccurrence, EventHandlingRecord, IncidentCase, MetricLogEvidence,
)
from app.models.document import Document, ManualRefinedDocument
from app.models.audit import SanitizedKnowledge
from app.schemas.incident import (
    EventChatRequest, EventChatResponse, EventChatEvidence, EventChatMessage,
)

logger = logging.getLogger(__name__)


class EventChatService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.OPENAI_MODEL

    async def chat(
        self, occurrence_id: int, request: EventChatRequest
    ) -> EventChatResponse:
        event = await self._load_event(occurrence_id)
        if not event:
            return EventChatResponse(
                answer="해당 이벤트를 찾을 수 없습니다.",
                evidence=[],
                limitation_flags=["event_not_found"],
                requires_manual_confirmation=True,
            )

        context, evidence, limitation_flags = await self._build_event_context(
            event, request.use_sanitized_knowledge
        )

        answer = await self._generate_response(
            query=request.query,
            event_context=context,
            conversation_history=request.conversation_history,
        )

        limitation_notice = None
        if limitation_flags:
            notices = []
            for flag in limitation_flags:
                if "protected" in flag:
                    notices.append("일부 관련 문서가 보호되어 있어 제한된 정보만 활용되었습니다.")
                    break
            limitation_notice = " ".join(notices) if notices else None

        return EventChatResponse(
            answer=answer,
            evidence=evidence,
            limitation_notice=limitation_notice,
            limitation_flags=limitation_flags,
            requires_manual_confirmation=len(limitation_flags) > 0,
            conversation_id=str(uuid.uuid4()),
        )

    async def _load_event(self, occurrence_id: int) -> Optional[EventOccurrence]:
        result = await self.db.execute(
            select(EventOccurrence)
            .options(
                selectinload(EventOccurrence.state_history),
                selectinload(EventOccurrence.handling_records),
                selectinload(EventOccurrence.assessment),
                selectinload(EventOccurrence.metric_log_evidence),
            )
            .where(EventOccurrence.id == occurrence_id)
        )
        return result.scalar_one_or_none()

    async def _build_event_context(
        self, event: EventOccurrence, use_sanitized: bool
    ) -> Tuple[str, List[EventChatEvidence], List[str]]:
        evidence: List[EventChatEvidence] = []
        limitation_flags: List[str] = []

        parts = [
            f"[Current Event]",
            f"Name: {event.event_name}",
            f"Host: {event.host or 'unknown'}",
            f"Severity: {event.severity}",
            f"Status: {event.current_status}",
            f"Occurrences: {event.occurrence_count}",
            f"First seen: {event.first_seen_at}",
            f"Last seen: {event.last_seen_at}",
        ]

        evidence.append(EventChatEvidence(
            source_id=str(event.id),
            source_type="event",
            title=event.event_name,
            content_preview=f"{event.severity} on {event.host}",
            relevance_score=1.0,
        ))

        if event.assessment:
            parts.append(f"\n[Assessment]")
            parts.append(f"Risk score: {event.assessment.risk_score}")
            parts.append(f"Pattern: {event.assessment.pattern_summary}")
            if event.assessment.probable_cause:
                parts.append(f"Probable cause: {event.assessment.probable_cause}")

        if event.handling_records:
            parts.append(f"\n[Recent Actions ({len(event.handling_records)})]")
            for hr in event.handling_records[:5]:
                parts.append(f"- [{hr.action_type}] {hr.action_summary} (by {hr.actor})")

        related_docs = await self._find_related_documents(event)
        if related_docs:
            parts.append(f"\n[Related Documents ({len(related_docs)})]")
            for doc in related_docs:
                refined = await self._get_refined_content(doc.id)

                if refined:
                    parts.append(f"- {doc.title}: {refined.content[:500]}")
                    evidence.append(EventChatEvidence(
                        source_id=str(doc.id),
                        source_type="refined_document",
                        title=doc.title,
                        content_preview=refined.content[:200],
                        relevance_score=0.8,
                    ))
                elif doc.processing_capability in ["fulltext_extractable", "chunkable", "embeddable"]:
                    parts.append(f"- {doc.title}: {doc.description or 'No description'}")
                    evidence.append(EventChatEvidence(
                        source_id=str(doc.id),
                        source_type="document",
                        title=doc.title,
                        content_preview=doc.description[:200] if doc.description else None,
                        relevance_score=0.7,
                    ))
                else:
                    parts.append(f"- {doc.title}: [Protected - metadata only]")
                    limitation_flags.append(f"document_{doc.id}_protected")
                    evidence.append(EventChatEvidence(
                        source_id=str(doc.id),
                        source_type="metadata",
                        title=doc.title,
                        content_preview="Protected document - metadata only",
                        relevance_score=0.3,
                    ))

        similar_incidents = await self._find_similar_incidents(event)
        if similar_incidents:
            parts.append(f"\n[Similar Incidents ({len(similar_incidents)})]")
            for inc in similar_incidents[:3]:
                parts.append(f"- {inc.title}: {inc.resolution_summary or 'no resolution'}")
                evidence.append(EventChatEvidence(
                    source_id=str(inc.id),
                    source_type="incident",
                    title=inc.title,
                    content_preview=inc.resolution_summary,
                    relevance_score=0.6,
                ))

        if use_sanitized:
            sanitized = await self._find_sanitized_knowledge(event)
            if sanitized:
                parts.append(f"\n[Operational Knowledge]")
                for sk in sanitized:
                    parts.append(f"- {sk.title}: {sk.content[:300]}")
                    evidence.append(EventChatEvidence(
                        source_id=str(sk.id),
                        source_type="sanitized_knowledge",
                        title=sk.title,
                        content_preview=sk.summary,
                        relevance_score=0.7,
                    ))

        return "\n".join(parts), evidence, limitation_flags

    async def _find_related_documents(self, event: EventOccurrence) -> List[Document]:
        keywords = [kw for kw in event.event_name.split() if len(kw) > 2][:3]
        if not keywords:
            return []

        keyword_filters = []
        for kw in keywords:
            keyword_filters.append(Document.title.ilike(f"%{kw}%"))
            keyword_filters.append(Document.tags.ilike(f"%{kw}%"))

        result = await self.db.execute(
            select(Document).where(
                Document.customer_id == event.customer_id,
                Document.is_active == True,
                or_(*keyword_filters),
            ).limit(5)
        )
        return list(result.scalars().all())

    async def _get_refined_content(self, document_id: int) -> Optional[ManualRefinedDocument]:
        result = await self.db.execute(
            select(ManualRefinedDocument)
            .where(ManualRefinedDocument.original_document_id == document_id)
            .order_by(ManualRefinedDocument.version.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def _find_similar_incidents(self, event: EventOccurrence) -> List[IncidentCase]:
        keywords = [kw for kw in event.event_name.split() if len(kw) > 2][:3]
        if not keywords:
            return []

        keyword_filters = [IncidentCase.title.ilike(f"%{kw}%") for kw in keywords]

        result = await self.db.execute(
            select(IncidentCase).where(
                IncidentCase.customer_id == event.customer_id,
                or_(*keyword_filters),
            ).limit(5)
        )
        return list(result.scalars().all())

    async def _find_sanitized_knowledge(self, event: EventOccurrence) -> List[SanitizedKnowledge]:
        keywords = [kw for kw in event.event_name.split() if len(kw) > 2][:3]
        if not keywords:
            return []

        keyword_filters = []
        for kw in keywords:
            keyword_filters.append(SanitizedKnowledge.title.ilike(f"%{kw}%"))
            keyword_filters.append(SanitizedKnowledge.content.ilike(f"%{kw}%"))

        result = await self.db.execute(
            select(SanitizedKnowledge).where(
                SanitizedKnowledge.status == "approved",
                or_(*keyword_filters),
            ).limit(3)
        )
        return list(result.scalars().all())

    async def _generate_response(
        self,
        query: str,
        event_context: str,
        conversation_history: Optional[List[EventChatMessage]],
    ) -> str:
        messages = [
            {
                "role": "system",
                "content": (
                    "You are an MSP operations expert assisting with event analysis.\n"
                    "You have access to the current event context, related documents, and historical data.\n"
                    "Rules:\n"
                    "1. Always respond in Korean when the query is in Korean\n"
                    "2. Cite specific sources when available\n"
                    "3. Clearly indicate when information is limited due to protected documents\n"
                    "4. Provide actionable recommendations\n"
                    "5. Be concise but thorough"
                ),
            },
            {
                "role": "user",
                "content": f"Event Context:\n{event_context}",
            },
        ]

        if conversation_history:
            for msg in conversation_history:
                messages.append({"role": msg.role, "content": msg.content})

        messages.append({"role": "user", "content": query})

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=2000,
            )
            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"Event chat generation failed: {e}")
            return "죄송합니다. 응답 생성 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요."
