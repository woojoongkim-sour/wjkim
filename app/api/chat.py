from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
import uuid

from app.core.database import get_db
from app.schemas.common import ChatRequest, ChatResponse
from app.models.document import Document, ManualRefinedDocument
from app.models.event import EventOccurrence, IncidentCase
from app.models.audit import SanitizedKnowledge

router = APIRouter()


@router.post("", response_model=ChatResponse)
async def chat_query(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db)
):
    conversation_id = str(uuid.uuid4())
    
    context_docs = []
    limitation_notice = None
    
    if request.context_ids:
        for doc_id in request.context_ids[:5]:
            result = await db.execute(
                select(Document).where(Document.id == doc_id)
            )
            doc = result.scalar_one_or_none()
            if doc:
                refined_result = await db.execute(
                    select(ManualRefinedDocument)
                    .where(ManualRefinedDocument.original_document_id == doc_id)
                    .order_by(ManualRefinedDocument.version.desc())
                    .limit(1)
                )
                refined = refined_result.scalar_one_or_none()
                
                context_text = ""
                if refined:
                    context_text = f"[Refined Document] {refined.content}"
                elif doc.processing_capability in ["fulltext_extractable", "chunkable"]:
                    context_text = f"[Document] {doc.description or doc.title}"
                else:
                    context_text = f"[Document Metadata Only] {doc.title}"
                    if not refined:
                        limitation_notice = f"Document '{doc.title}' is protected. Content may be limited."
                
                context_docs.append({
                    "id": doc.id,
                    "type": "document",
                    "content": context_text,
                    "title": doc.title
                })
    
    evidence = []
    for doc in context_docs:
        evidence.append({
            "id": doc["id"],
            "type": doc["type"],
            "title": doc["title"],
            "content_preview": doc["content"][:200] if doc["content"] else None
        })
    
    answer = f"Based on the query '{request.query}', I found {len(context_docs)} relevant documents."
    
    if context_docs:
        answer += "\n\nHere are the relevant findings:\n"
        for i, doc in enumerate(context_docs, 1):
            answer += f"\n{i}. **{doc['title']}**\n   {doc['content'][:500]}...\n"
    else:
        answer += "\n\nNo directly relevant documents were found. Please try a more specific query or check if documents have been uploaded and processed."
    
    if limitation_notice:
        answer += f"\n\n⚠️ {limitation_notice}"
    
    return ChatResponse(
        answer=answer,
        evidence=evidence,
        source_representation="document_metadata",
        limitation_notice=limitation_notice,
        requires_manual_confirmation=limitation_notice is not None,
        conversation_id=conversation_id
    )


@router.post("/enrich-event")
async def enrich_event(
    occurrence_id: int,
    customer_id: int,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(EventOccurrence).where(
            EventOccurrence.id == occurrence_id,
            EventOccurrence.customer_id == customer_id
        )
    )
    event = result.scalar_one_or_none()
    
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    related_docs_result = await db.execute(
        select(Document).where(
            Document.customer_id == customer_id,
            Document.is_active == True
        ).limit(10)
    )
    related_docs = related_docs_result.scalars().all()
    
    incidents_result = await db.execute(
        select(IncidentCase).where(
            IncidentCase.customer_id == customer_id
        ).limit(5)
    )
    related_incidents = incidents_result.scalars().all()
    
    limitation_flags = []
    
    recommended_actions = [
        "Check server connectivity",
        "Review recent configuration changes",
        "Verify service dependencies",
        "Check monitoring thresholds"
    ]
    
    related_docs_response = []
    for doc in related_docs:
        if doc.protection_type != "none" and not doc.is_refined:
            limitation_flags.append(f"Document {doc.id} is protected")
            related_docs_response.append({
                "id": doc.id,
                "title": doc.title,
                "type": doc.document_type,
                "content_available": False,
                "limitation": f"Protected by {doc.protection_type}"
            })
        else:
            related_docs_response.append({
                "id": doc.id,
                "title": doc.title,
                "type": doc.document_type,
                "content_available": True
            })
    
    return {
        "occurrence_id": occurrence_id,
        "event_summary": f"{event.event_name} on {event.host or 'unknown host'}",
        "related_documents": related_docs_response,
        "related_incidents": [
            {"id": i.id, "title": i.title, "resolution_summary": i.resolution_summary}
            for i in related_incidents
        ],
        "recommended_actions": recommended_actions,
        "metric_log_evidence": [],
        "limitation_flags": limitation_flags
    }
