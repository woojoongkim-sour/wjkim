import logging
from typing import Optional, List
from openai import AsyncOpenAI
from openai.pydantic_function_builder import PydanticFunction
from pydantic import BaseModel, Field
from app.core.config import settings
from app.schemas.ai import (
    ChatRequest, ChatResponse, Evidence, SourceType, LimitationFlag
)

logger = logging.getLogger(__name__)


class ArchiveAnswerResponse(BaseModel):
    answer: str
    limitation_flags: List[str] = Field(default_factory=list)
    requires_confirmation: bool = False


class ArchiveChatAgent:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.GEMINI_API_KEY, base_url=settings.GEMINI_BASE_URL)
        self.model = settings.GEMINI_MODEL
        self.system_prompt = """You are an expert assistant for MSP (Managed Service Provider) operations.
Your role is to help operators find relevant information from the archive.

CRITICAL RULES:
1. Always cite your sources in the response
2. Clearly indicate when information comes from protected documents (metadata only)
3. When full content is unavailable, suggest checking the original document or requesting refined content
4. Be concise but thorough
5. Format your response in Korean when the query is in Korean

If you cannot find relevant information, say so clearly."""

    async def chat(self, request: ChatRequest) -> ChatResponse:
        try:
            messages = [
                {"role": "system", "content": self.system_prompt}
            ]
            
            if request.conversation_history:
                for msg in request.conversation_history:
                    messages.append({
                        "role": msg.role,
                        "content": msg.content
                    })
            
            context_prompt = self._build_context_prompt(request)
            messages.append({
                "role": "user",
                "content": f"{context_prompt}\n\nQuestion: {request.query}"
            })
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=2000
            )
            
            answer = response.choices[0].message.content
            
            evidence = self._build_evidence_from_context(request)
            limitation_flags = self._detect_limitations(request)
            
            return ChatResponse(
                answer=answer,
                evidence=evidence,
                source_representation=self._get_source_representation(evidence),
                limitation_notice=self._build_limitation_notice(limitation_flags),
                limitation_flags=limitation_flags,
                requires_manual_confirmation=len(limitation_flags) > 0
            )
            
        except Exception as e:
            logger.error(f"Chat agent error: {e}")
            return ChatResponse(
                answer="죄송합니다. 응답 생성 중 오류가 발생했습니다.",
                evidence=[],
                source_representation="error",
                limitation_flags=[LimitationFlag.EXTERNAL_CONTENT_UNAVAILABLE],
                requires_manual_confirmation=True
            )

    def _build_context_prompt(self, request: ChatRequest) -> str:
        prompt_parts = [f"[Customer ID: {request.customer_id}]"]
        
        if request.use_sanitized_knowledge:
            prompt_parts.append("[Available: Sanitized operational knowledge]")
        
        prompt_parts.append(
            "[Data Sources Available]: "
            "Documents, Refined Documents, Event History, Incident Cases, "
            "Operational Knowledge (sanitized), Server/Service Inventory"
        )
        
        if request.context_ids:
            prompt_parts.append(f"[Specific Context IDs: {request.context_ids}]")
        
        return "\n".join(prompt_parts)

    def _build_evidence_from_context(self, request: ChatRequest) -> List[Evidence]:
        return []

    def _detect_limitations(self, request: ChatRequest) -> List[LimitationFlag]:
        flags = []
        if not request.use_sanitized_knowledge:
            flags.append(LimitationFlag.EXTERNAL_CONTENT_UNAVAILABLE)
        return flags

    def _get_source_representation(self, evidence: List[Evidence]) -> str:
        if not evidence:
            return "no_sources"
        
        source_types = set(e.type for e in evidence)
        if SourceType.REFINED_DOCUMENT in source_types:
            return "refined_documents"
        elif SourceType.DOCUMENT in source_types:
            return "original_documents"
        else:
            return "mixed_sources"

    def _build_limitation_notice(self, flags: List[LimitationFlag]) -> Optional[str]:
        if not flags:
            return None
        
        notices = []
        if LimitationFlag.PROTECTED_DOCUMENT in flags:
            notices.append("일부 문서가 보호되어 있어 메타데이터만 활용되었습니다.")
        if LimitationFlag.METADATA_ONLY in flags:
            notices.append("원본 내용을 확인할 수 없는 문서가 포함되어 있습니다.")
        if LimitationFlag.NO_REFINED_CONTENT in flags:
            notices.append("수동 정제본이 없는 문서는 정확한 답변 보장이 어렵습니다.")
        
        return " | ".join(notices) if notices else None


chat_agent = ArchiveChatAgent()
