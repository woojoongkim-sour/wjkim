from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from typing import List, Optional

from app.core.database import get_db
from app.models.document import Document, ManualRefinedDocument, DocumentChunk
from app.models.event import EventOccurrence
from app.schemas.common import SearchRequest, SearchResponse

router = APIRouter()


@router.post("", response_model=SearchResponse)
async def search_archive(
    request: SearchRequest,
    db: AsyncSession = Depends(get_db)
):
    results = []
    limitation_notices = []
    
    query = select(Document).where(
        Document.customer_id == request.customer_id,
        Document.is_active == True
    )
    
    if request.query:
        search_term = f"%{request.query}%"
        query = query.where(
            or_(
                Document.title.ilike(search_term),
                Document.description.ilike(search_term),
                Document.tags.ilike(search_term)
            )
        )
    
    result = await db.execute(query.limit(request.limit))
    documents = result.scalars().all()
    
    for doc in documents:
        content_available = doc.processing_capability in [
            "fulltext_extractable", "chunkable", "embeddable"
        ]
        refined_available = doc.is_refined
        
        limitation = None
        if doc.protection_type != "none" and not doc.is_refined:
            limitation = f"Protected by {doc.protection_type}. Content may be limited."
            limitation_notices.append(limitation)
        
        results.append({
            "id": doc.id,
            "type": "document",
            "title": doc.title,
            "snippet": doc.description,
            "matched_by": "metadata",
            "indexing_status": doc.processing_status,
            "protection_type": doc.protection_type,
            "content_available": content_available,
            "refined_available": refined_available,
            "limitation_notice": limitation,
            "score": 1.0
        })
    
    return SearchResponse(
        results=results,
        total=len(results),
        limitation_notices=limitation_notices
    )


@router.post("/similar-events")
async def search_similar_events(
    occurrence_id: int,
    customer_id: int,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(EventOccurrence).where(EventOccurrence.id == occurrence_id)
    )
    target_event = result.scalar_one_or_none()
    
    if not target_event:
        return {"similar_events": [], "similarity_reason": "Event not found"}
    
    similar = await db.execute(
        select(EventOccurrence).where(
            EventOccurrence.customer_id == customer_id,
            EventOccurrence.id != occurrence_id,
            EventOccurrence.event_name == target_event.event_name,
            EventOccurrence.is_active == True
        ).limit(10)
    )
    
    similar_events = similar.scalars().all()
    
    return {
        "similar_events": [
            {
                "id": e.id,
                "event_name": e.event_name,
                "severity": e.severity,
                "host": e.host,
                "current_status": e.current_status,
                "first_seen_at": e.first_seen_at.isoformat() if e.first_seen_at else None,
                "occurrence_count": e.occurrence_count
            }
            for e in similar_events
        ],
        "similarity_reason": f"Same event name: {target_event.event_name}"
    }


@router.post("/similar-incidents")
async def search_similar_incidents(
    query: str,
    customer_id: int,
    db: AsyncSession = Depends(get_db)
):
    from app.models.event import IncidentCase
    
    result = await db.execute(
        select(IncidentCase).where(
            IncidentCase.customer_id == customer_id,
            or_(
                IncidentCase.title.ilike(f"%{query}%"),
                IncidentCase.description.ilike(f"%{query}%"),
                IncidentCase.tags.ilike(f"%{query}%")
            )
        ).limit(10)
    )
    
    incidents = result.scalars().all()
    
    return {
        "incidents": [
            {
                "id": i.id,
                "title": i.title,
                "severity": i.severity,
                "occurred_at": i.occurred_at.isoformat() if i.occurred_at else None,
                "resolution_summary": i.resolution_summary
            }
            for i in incidents
        ]
    }


@router.post("/graph-context")
async def get_graph_context(
    entity_id: str,
    entity_type: str,
    customer_id: int,
    depth: int = 2,
    db: AsyncSession = Depends(get_db)
):
    nodes = []
    edges = []
    
    if entity_type == "document":
        result = await db.execute(
            select(Document).where(
                Document.id == int(entity_id),
                Document.customer_id == customer_id
            )
        )
        doc = result.scalar_one_or_none()
        
        if doc:
            nodes.append({
                "id": f"doc_{doc.id}",
                "type": "document",
                "label": doc.title,
                "properties": {
                    "document_type": doc.document_type,
                    "processing_status": doc.processing_status
                }
            })
            
            if doc.refined_documents:
                for refined in doc.refined_documents:
                    nodes.append({
                        "id": f"refined_{refined.id}",
                        "type": "refined_document",
                        "label": refined.summary or "Refined Document",
                        "properties": {"status": refined.status}
                    })
                    edges.append({
                        "source": f"doc_{doc.id}",
                        "target": f"refined_{refined.id}",
                        "type": "has_refined",
                        "properties": {}
                    })
    
    return {
        "nodes": nodes,
        "edges": edges,
        "source_types": ["metadata"],
        "confidence": {}
    }
