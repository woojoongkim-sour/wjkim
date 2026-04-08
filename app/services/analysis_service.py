import logging
from datetime import datetime, timedelta
from typing import List, Optional

from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.models.event import (
    EventOccurrence, EventStateHistory, EventHandlingRecord,
    EventAssessment, MetricLogEvidence, IncidentCase,
)
from app.models.document import Document
from app.models.audit import SanitizedKnowledge
from app.schemas.incident import AnalysisReportResponse

logger = logging.getLogger(__name__)


class AnalysisService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.OPENAI_MODEL

    async def generate_analysis_report(self, occurrence_id: int) -> AnalysisReportResponse:
        event = await self._load_event_with_relations(occurrence_id)
        if not event:
            raise ValueError(f"Event {occurrence_id} not found")

        recurrence = await self._analyze_recurrence(event)
        similar_incidents = await self._find_similar_incidents(event)
        related_docs = await self._find_related_documents(event)
        evidence_items = await self._get_evidence(event)

        limitation_flags = self._detect_limitations(related_docs)

        context = self._build_analysis_context(event, recurrence, similar_incidents, related_docs, evidence_items)

        ai_analysis = await self._run_ai_analysis(context, event)

        assessment = await self._save_assessment(event, ai_analysis, recurrence)

        return AnalysisReportResponse(
            occurrence_id=occurrence_id,
            event_name=event.event_name,
            generated_at=datetime.utcnow(),
            analyzer_type="auto",
            summary=ai_analysis["summary"],
            probable_causes=ai_analysis["probable_causes"],
            risk_level=ai_analysis["risk_level"],
            risk_score=ai_analysis["risk_score"],
            recurrence_analysis=recurrence["analysis"],
            recurrence_score=recurrence["score"],
            recommended_actions=ai_analysis["recommended_actions"],
            related_patterns=ai_analysis["related_patterns"],
            evidence_used=[
                {"type": "event_history", "count": len(event.state_history)},
                {"type": "handling_records", "count": len(event.handling_records)},
                {"type": "similar_incidents", "count": len(similar_incidents)},
                {"type": "related_documents", "count": len(related_docs)},
                {"type": "metric_log_evidence", "count": len(evidence_items)},
            ],
            limitation_flags=limitation_flags,
        )

    async def _load_event_with_relations(self, occurrence_id: int) -> Optional[EventOccurrence]:
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

    async def _analyze_recurrence(self, event: EventOccurrence) -> dict:
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)

        result = await self.db.execute(
            select(func.count(EventOccurrence.id)).where(
                and_(
                    EventOccurrence.customer_id == event.customer_id,
                    EventOccurrence.event_name == event.event_name,
                    EventOccurrence.host == event.host,
                    EventOccurrence.first_seen_at >= thirty_days_ago,
                )
            )
        )
        count_30d = result.scalar() or 0

        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        result_7d = await self.db.execute(
            select(func.count(EventOccurrence.id)).where(
                and_(
                    EventOccurrence.customer_id == event.customer_id,
                    EventOccurrence.event_name == event.event_name,
                    EventOccurrence.host == event.host,
                    EventOccurrence.first_seen_at >= seven_days_ago,
                )
            )
        )
        count_7d = result_7d.scalar() or 0

        score = min(100, count_30d * 5 + count_7d * 15)

        if count_7d >= 10:
            analysis = f"빈번한 반복: 최근 7일간 {count_7d}회, 30일간 {count_30d}회 발생. 근본 원인 조사 필요."
        elif count_30d >= 5:
            analysis = f"주기적 반복: 최근 30일간 {count_30d}회 발생 (7일간 {count_7d}회). 패턴 확인 권장."
        elif count_30d >= 2:
            analysis = f"간헐적 반복: 최근 30일간 {count_30d}회 발생. 모니터링 유지."
        else:
            analysis = f"신규 또는 희귀 이벤트: 최근 30일간 {count_30d}회 발생."

        return {"count_7d": count_7d, "count_30d": count_30d, "score": score, "analysis": analysis}

    async def _find_similar_incidents(self, event: EventOccurrence) -> List[IncidentCase]:
        keywords = event.event_name.split()[:3]
        conditions = [IncidentCase.customer_id == event.customer_id]

        from sqlalchemy import or_
        keyword_filters = [IncidentCase.title.ilike(f"%{kw}%") for kw in keywords if len(kw) > 2]
        if keyword_filters:
            conditions.append(or_(*keyword_filters))

        result = await self.db.execute(
            select(IncidentCase).where(and_(*conditions)).limit(5)
        )
        return list(result.scalars().all())

    async def _find_related_documents(self, event: EventOccurrence) -> List[Document]:
        keywords = event.event_name.split()[:3]
        from sqlalchemy import or_

        keyword_filters = []
        for kw in keywords:
            if len(kw) > 2:
                keyword_filters.append(Document.title.ilike(f"%{kw}%"))
                keyword_filters.append(Document.tags.ilike(f"%{kw}%"))

        if not keyword_filters:
            return []

        result = await self.db.execute(
            select(Document).where(
                and_(
                    Document.customer_id == event.customer_id,
                    Document.is_active == True,
                    or_(*keyword_filters),
                )
            ).limit(10)
        )
        return list(result.scalars().all())

    async def _get_evidence(self, event: EventOccurrence) -> List[MetricLogEvidence]:
        return list(event.metric_log_evidence) if event.metric_log_evidence else []

    def _detect_limitations(self, documents: List[Document]) -> List[str]:
        flags = []
        for doc in documents:
            if doc.protection_type != "none" and not doc.is_refined:
                flags.append(f"document_{doc.id}_protected_by_{doc.protection_type}")
        return flags

    def _build_analysis_context(
        self,
        event: EventOccurrence,
        recurrence: dict,
        incidents: List[IncidentCase],
        documents: List[Document],
        evidence: List[MetricLogEvidence],
    ) -> str:
        parts = [
            f"Event: {event.event_name}",
            f"Host: {event.host or 'unknown'}",
            f"Severity: {event.severity}",
            f"Status: {event.current_status}",
            f"Occurrence count: {event.occurrence_count}",
            f"First seen: {event.first_seen_at}",
            f"Last seen: {event.last_seen_at}",
            f"\nRecurrence: {recurrence['analysis']}",
        ]

        if event.state_history:
            parts.append(f"\nState changes ({len(event.state_history)}):")
            for sh in event.state_history[:5]:
                parts.append(f"  {sh.changed_at}: {sh.previous_state} -> {sh.new_state}")

        if event.handling_records:
            parts.append(f"\nHandling records ({len(event.handling_records)}):")
            for hr in event.handling_records[:5]:
                parts.append(f"  {hr.executed_at}: [{hr.action_type}] {hr.action_summary}")

        if incidents:
            parts.append(f"\nSimilar incidents ({len(incidents)}):")
            for inc in incidents[:3]:
                parts.append(f"  - {inc.title}: {inc.resolution_summary or 'no resolution recorded'}")

        if documents:
            parts.append(f"\nRelated documents ({len(documents)}):")
            for doc in documents[:5]:
                available = "content available" if doc.processing_capability in ["fulltext_extractable", "chunkable", "embeddable"] else "metadata only"
                parts.append(f"  - {doc.title} ({available})")

        if evidence:
            parts.append(f"\nMetric/Log evidence ({len(evidence)}):")
            for ev in evidence[:3]:
                parts.append(f"  - [{ev.evidence_type}] {ev.summary}")

        return "\n".join(parts)

    async def _run_ai_analysis(self, context: str, event: EventOccurrence) -> dict:
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an MSP incident analysis expert. Analyze the event and provide a structured report.\n"
                            "Respond in JSON with these exact keys:\n"
                            "- summary: Brief analysis summary (Korean)\n"
                            "- probable_causes: List of probable cause strings (Korean)\n"
                            "- risk_level: one of 'critical', 'high', 'medium', 'low'\n"
                            "- risk_score: integer 0-100\n"
                            "- recommended_actions: List of recommended action strings (Korean)\n"
                            "- related_patterns: List of related pattern description strings (Korean)"
                        ),
                    },
                    {"role": "user", "content": f"Analyze this event:\n\n{context}"},
                ],
                temperature=0.3,
                max_tokens=1500,
                response_format={"type": "json_object"},
            )

            import json
            result = json.loads(response.choices[0].message.content)

            return {
                "summary": result.get("summary", "분석 결과를 생성할 수 없습니다."),
                "probable_causes": result.get("probable_causes", []),
                "risk_level": result.get("risk_level", "medium"),
                "risk_score": max(0, min(100, result.get("risk_score", 50))),
                "recommended_actions": result.get("recommended_actions", []),
                "related_patterns": result.get("related_patterns", []),
            }

        except Exception as e:
            logger.error(f"AI analysis failed: {e}")
            return self._fallback_analysis(event)

    def _fallback_analysis(self, event: EventOccurrence) -> dict:
        severity_risk = {
            "critical": 90, "high": 70, "medium": 50, "low": 30, "info": 10
        }
        risk_score = severity_risk.get(str(event.severity), 50)

        return {
            "summary": f"{event.event_name} 이벤트가 {event.host or 'unknown'}에서 발생했습니다. 자동 분석이 실패하여 기본 정보를 제공합니다.",
            "probable_causes": ["자동 분석 실패 - 수동 확인 필요"],
            "risk_level": str(event.severity) if str(event.severity) in ["critical", "high", "medium", "low"] else "medium",
            "risk_score": risk_score,
            "recommended_actions": [
                "서버 상태 확인",
                "최근 변경사항 검토",
                "관련 서비스 의존성 점검",
            ],
            "related_patterns": [],
        }

    async def _save_assessment(
        self, event: EventOccurrence, analysis: dict, recurrence: dict
    ) -> EventAssessment:
        existing = event.assessment
        if existing:
            existing.recurrence_score = recurrence["score"]
            existing.risk_score = analysis["risk_score"]
            existing.pattern_summary = analysis["summary"]
            existing.probable_cause = "; ".join(analysis["probable_causes"])
            existing.analyzed_at = datetime.utcnow()
            existing.analyzer_type = "auto"
            await self.db.commit()
            return existing

        assessment = EventAssessment(
            occurrence_id=event.id,
            recurrence_score=recurrence["score"],
            risk_score=analysis["risk_score"],
            pattern_summary=analysis["summary"],
            probable_cause="; ".join(analysis["probable_causes"]),
            transfer_to_incident=analysis["risk_score"] >= 80,
            analyzed_at=datetime.utcnow(),
            analyzer_type="auto",
        )
        self.db.add(assessment)
        await self.db.commit()
        await self.db.refresh(assessment)
        return assessment
