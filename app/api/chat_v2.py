from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from typing import List, Optional
from datetime import datetime

from app.core.database import get_db
from app.schemas.ai import ChatRequest, ChatResponse, EnrichRequest, EnrichResponse, EnrichEvidence, LimitationFlag
from app.services.chat_agent import chat_agent
from app.services.search_service import SemanticSearchService, VectorSearchService
from app.services.document_service import DocumentEnricher
from app.models.event import EventOccurrence, IncidentCase, EventStateHistory, EventHandlingRecord
from app.models.document import Document
from app.core.audit import create_audit_log
from app.models.enums import AuditAction

router = APIRouter()


@router.post("", response_model=ChatResponse)
async def chat_query(
    request: ChatRequest,
    request_data: Request,
    db: AsyncSession = Depends(get_db)
):
    semantic_search = SemanticSearchService(db)
    search_results = await semantic_search.search(
        query=request.query,
        customer_id=request.customer_id,
        use_sanitized=request.use_sanitized_knowledge
    )
    
    if search_results["documents"]:
        vector_search = VectorSearchService(db)
        vector_results = await vector_search.search_documents(
            query=request.query,
            customer_id=request.customer_id
        )
        
        for vr in vector_results:
            if vr["id"] not in [d["id"] for d in search_results["documents"]]:
                search_results["documents"].append(vr)
    
    limitation_flags = [LimitationFlag(f) for f in search_results.get("limitation_flags", [])]
    
    chat_response = await chat_agent.chat(request)
    
    chat_response.evidence = [
        {
            "id": d["id"],
            "type": "document",
            "title": d["title"],
            "content_preview": d.get("snippet"),
            "matched_by": d.get("matched_by", "unknown"),
            "limitation": d.get("limitation")
        }
        for d in search_results["documents"][:10]
    ]
    
    if limitation_flags:
        chat_response.limitation_flags = limitation_flags
        chat_response.requires_manual_confirmation = True
    
    await create_audit_log(
        customer_id=request.customer_id,
        user_id=None,
        action=AuditAction.CHAT_REQUEST,
        metadata={
            "query": request.query,
            "sources_found": len(search_results["documents"]),
            "limitations": [f.value for f in limitation_flags]
        }
    )
    
    return chat_response


@router.post("/enrich-event", response_model=EnrichResponse)
async def enrich_event(
    request: EnrichRequest,
    db: AsyncSession = Depends(get_db)
):
    event_result = await db.execute(
        select(EventOccurrence).where(
            EventOccurrence.id == request.occurrence_id,
            EventOccurrence.customer_id == request.customer_id
        )
    )
    event = event_result.scalar_one_or_none()
    
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    related_docs_result = await db.execute(
        select(Document).where(
            Document.customer_id == request.customer_id,
            Document.is_active == True
        ).limit(20)
    )
    related_docs = related_docs_result.scalars().all()
    
    related_incidents_result = await db.execute(
        select(IncidentCase).where(
            IncidentCase.customer_id == request.customer_id
        ).limit(10)
    )
    related_incidents = related_incidents_result.scalars().all()
    
    limitation_flags = []
    related_docs_response = []
    
    for doc in related_docs:
        content_available = doc.processing_capability in [
            "fulltext_extractable", "chunkable", "embeddable"
        ] or doc.is_refined
        
        limitation = None
        if doc.protection_type != "none" and not doc.is_refined:
            limitation = f"Protected by {doc.protection_type}"
            limitation_flags.append(LimitationFlag.PROTECTED_DOCUMENT)
        
        if not content_available and not doc.is_refined:
            limitation_flags.append(LimitationFlag.METADATA_ONLY)
        
        related_docs_response.append(EnrichEvidence(
            id=doc.id,
            type="document",
            title=doc.title,
            content_available=content_available,
            limitation=limitation
        ))
    
    recommended_actions = [
        "Check server connectivity and service status",
        "Review recent configuration changes",
        "Verify monitoring thresholds and alerts",
        "Check related incidents for similar patterns",
        "Review relevant documentation and runbooks"
    ]
    
    await create_audit_log(
        customer_id=request.customer_id,
        user_id=None,
        action=AuditAction.ENRICH_REQUEST,
        resource_type="event",
        resource_id=str(request.occurrence_id),
        metadata={
            "related_docs": len(related_docs),
            "related_incidents": len(related_incidents),
            "limitations": [f.value for f in limitation_flags]
        }
    )
    
    return EnrichResponse(
        occurrence_id=request.occurrence_id,
        event_summary=f"{event.event_name} on {event.host or 'unknown'}",
        related_documents=related_docs_response,
        related_incidents=[
            {
                "id": i.id,
                "title": i.title,
                "resolution_summary": i.resolution_summary,
                "severity": i.severity
            }
            for i in related_incidents
        ],
        recommended_actions=recommended_actions,
        metric_log_evidence=[],
        limitation_flags=limitation_flags
    )
