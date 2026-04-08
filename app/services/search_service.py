import logging
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_
from app.models.document import Document, ManualRefinedDocument, DocumentChunk
from app.models.event import EventOccurrence, IncidentCase, EventHandlingRecord
from app.models.audit import SanitizedKnowledge
from app.services.embedding import embedding_service
from app.schemas.ai import Citation, SourceType, LimitationFlag
import json

logger = logging.getLogger(__name__)


class VectorSearchService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def search_documents(
        self,
        query: str,
        customer_id: int,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        try:
            query_embedding = await embedding_service.create_embedding(query)
            
            result = await self.db.execute(
                select(DocumentChunk, Document)
                .join(Document, DocumentChunk.document_id == Document.id)
                .where(
                    Document.customer_id == customer_id,
                    Document.is_active == True,
                    Document.processing_capability.in_([
                        "fulltext_extractable", "chunkable", "embeddable"
                    ])
                )
                .limit(limit * 3)
            )
            
            chunks_with_docs = result.all()
            
            scored_chunks = []
            for chunk, doc in chunks_with_docs:
                if chunk.embedding:
                    import pickle
                    chunk_vector = pickle.loads(chunk.embedding)
                    similarity = self._cosine_similarity(query_embedding, chunk_vector)
                    scored_chunks.append({
                        "chunk": chunk,
                        "document": doc,
                        "score": similarity
                    })
            
            scored_chunks.sort(key=lambda x: x["score"], reverse=True)
            
            results = []
            seen_docs = set()
            for item in scored_chunks[:limit]:
                doc = item["document"]
                if doc.id not in seen_docs:
                    seen_docs.add(doc.id)
                    results.append({
                        "id": doc.id,
                        "title": doc.title,
                        "document_type": doc.document_type,
                        "snippet": item["chunk"].content[:500],
                        "score": item["score"],
                        "matched_by": "vector",
                        "content_available": True,
                        "limitation": None
                    })
            
            return results
            
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = sum(a * a for a in vec1) ** 0.5
        magnitude2 = sum(b * b for b in vec2) ** 0.5
        
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        
        return dot_product / (magnitude1 * magnitude2)


class SemanticSearchService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def search(
        self,
        query: str,
        customer_id: int,
        limit: int = 10,
        use_sanitized: bool = True
    ) -> Dict[str, Any]:
        results = {
            "documents": [],
            "incidents": [],
            "sanitized_knowledge": [],
            "citations": [],
            "limitation_flags": []
        }
        
        search_term = f"%{query}%"
        
        doc_result = await self.db.execute(
            select(Document)
            .where(
                Document.customer_id == customer_id,
                Document.is_active == True,
                or_(
                    Document.title.ilike(search_term),
                    Document.description.ilike(search_term),
                    Document.tags.ilike(search_term)
                )
            )
            .limit(limit)
        )
        documents = doc_result.scalars().all()
        
        for doc in documents:
            content_available = doc.processing_capability in [
                "fulltext_extractable", "chunkable", "embeddable"
            ]
            is_refined = doc.is_refined
            
            limitation = None
            if doc.protection_type != "none" and not is_refined:
                limitation = f"Protected by {doc.protection_type}"
                results["limitation_flags"].append(LimitationFlag.PROTECTED_DOCUMENT.value)
            
            if not content_available and not is_refined:
                results["limitation_flags"].append(LimitationFlag.METADATA_ONLY.value)
            
            results["documents"].append({
                "id": doc.id,
                "title": doc.title,
                "document_type": doc.document_type,
                "snippet": doc.description,
                "matched_by": "metadata",
                "content_available": content_available or is_refined,
                "refined_available": is_refined,
                "limitation": limitation,
                "score": 1.0
            })
            
            results["citations"].append(Citation(
                source_id=str(doc.id),
                source_type=SourceType.REFINED_DOCUMENT if is_refined else SourceType.DOCUMENT,
                title=doc.title,
                content_preview=doc.description[:200] if doc.description else None,
                relevance_score=0.8
            ))
        
        if use_sanitized:
            sanitized_result = await self.db.execute(
                select(SanitizedKnowledge)
                .where(
                    SanitizedKnowledge.status == "approved",
                    or_(
                        SanitizedKnowledge.title.ilike(search_term),
                        SanitizedKnowledge.content.ilike(search_term),
                        SanitizedKnowledge.tags.ilike(search_term)
                    )
                )
                .limit(5)
            )
            sanitized = sanitized_result.scalars().all()
            
            for knowledge in sanitized:
                results["sanitized_knowledge"].append({
                    "id": knowledge.id,
                    "title": knowledge.title,
                    "summary": knowledge.summary,
                    "content": knowledge.content,
                    "tags": knowledge.tags
                })
                results["citations"].append(Citation(
                    source_id=str(knowledge.id),
                    source_type=SourceType.SANITIZED_KNOWLEDGE,
                    title=knowledge.title,
                    content_preview=knowledge.summary,
                    relevance_score=0.9
                ))
        
        incident_result = await self.db.execute(
            select(IncidentCase)
            .where(
                IncidentCase.customer_id == customer_id,
                or_(
                    IncidentCase.title.ilike(search_term),
                    IncidentCase.description.ilike(search_term)
                )
            )
            .limit(5)
        )
        incidents = incident_result.scalars().all()
        
        for incident in incidents:
            results["incidents"].append({
                "id": incident.id,
                "title": incident.title,
                "severity": incident.severity,
                "occurred_at": incident.occurred_at.isoformat() if incident.occurred_at else None,
                "resolution_summary": incident.resolution_summary
            })
        
        return results
