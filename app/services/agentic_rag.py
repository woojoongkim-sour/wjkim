import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from openai import AsyncOpenAI
import json

from app.core.config import settings
from app.services.hybrid_search import HybridSearchService, HybridSearchRequest

logger = logging.getLogger(__name__)


class QueryComplexity(BaseModel):
    is_complex: bool
    reasoning: str
    suggested_approach: str  # single-pass | multi-step


class SearchQuery(BaseModel):
    query: str
    customer_id: int
    filters: Optional[Dict[str, Any]] = None
    cross_search: bool = False


class ToolCallResult(BaseModel):
    tool_name: str
    success: bool
    results: Any
    error: Optional[str] = None


class AgenticRAGAgent:
    def __init__(self, db_session):
        self.db = db_session
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.OPENAI_MODEL
        self.search_service = HybridSearchService(db_session)
        self.max_tool_calls = settings.AGENT_MAX_TOOL_CALLS
        self.timeout = settings.AGENT_TIMEOUT_SECONDS
        self.escalation_threshold = settings.ESCALATION_SCORE_THRESHOLD
        
        self.system_prompt = """You are an expert MSP (Managed Service Provider) operations assistant.

Your role is to help operators find relevant information from the document archive using available tools.

AVAILABLE TOOLS:
1. hybrid_search: Search documents using 3-way hybrid search (dense + sparse + keyword)
2. version_search: Search documents at a specific point in time
3. cross_search: Search across all customers for similar cases
4. graph_traverse: Explore relationships between entities

SEARCH RULES:
- For simple information requests (phone numbers, document existence): use hybrid_search
- For time-based queries ("what was the contact in October?"): use version_search
- For finding similar cases across customers: use cross_search
- Always cite your sources in the response

COMPLEXITY DETECTION:
- Simple: Single topic, direct question (e.g., "What's Kim's phone number?")
- Complex: Multi-step reasoning, comparisons, historical analysis needed

Respond in Korean when the query is in Korean."""

    async def analyze_complexity(self, query: str) -> QueryComplexity:
        """Analyze query complexity to determine routing strategy."""
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"Analyze this query's complexity:\n\nQuery: {query}\n\nDetermine if this is a 'simple' or 'complex' query. Simple queries can be answered with a single search. Complex queries require multi-step reasoning or multiple tool calls."}
        ]
        
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.3,
            max_tokens=500
        )
        
        answer = response.choices[0].message.content.lower()
        
        is_complex = "complex" in answer or "multi-step" in answer
        
        return QueryComplexity(
            is_complex=is_complex,
            reasoning=answer,
            suggested_approach="multi-step" if is_complex else "single-pass"
        )

    async def single_pass_search(self, request: HybridSearchRequest) -> Dict[str, Any]:
        """Execute single-pass RAG search."""
        search_result = await self.search_service.search(request)
        
        if not search_result.escalation_triggered:
            return {
                "mode": "single-pass",
                "search_results": search_result,
                "needs_escalation": False
            }
        
        return {
            "mode": "single-pass",
            "search_results": search_result,
            "needs_escalation": True
        }

    async def multi_step_search(
        self, query: str, customer_id: int, cross_search: bool = False
    ) -> List[ToolCallResult]:
        """Execute multi-step agentic search with tool orchestration."""
        tool_results = []
        query_decomposition = await self._decompose_query(query)
        
        for step_num, sub_query in enumerate(query_decomposition):
            if len(tool_results) >= self.max_tool_calls:
                logger.info(f"Max tool calls ({self.max_tool_calls}) reached")
                break
            
            tool_result = await self._execute_tool_call(
                sub_query, customer_id, cross_search
            )
            tool_results.append(tool_result)
            
            if self._is_sufficient(tool_results):
                break
            
            if tool_result.success and tool_result.results.get("total", 0) > 0:
                continue
            
            fallback_result = await self._execute_fallback(sub_query, customer_id)
            if fallback_result:
                tool_results.append(fallback_result)
        
        return tool_results

    async def _decompose_query(self, query: str) -> List[str]:
        """Decompose complex query into sub-queries."""
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"Decompose this complex query into search-friendly sub-queries:\n\nQuery: {query}\n\nReturn a JSON array of sub-queries. Each sub-query should be a self-contained search query."}
        ]
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.3,
                max_tokens=1000
            )
            
            content = response.choices[0].message.content
            if "[" in content:
                start = content.find("[")
                end = content.rfind("]") + 1
                return json.loads(content[start:end])
        except Exception as e:
            logger.warning(f"Query decomposition failed: {e}")
        
        return [query]

    async def _execute_tool_call(
        self, query: str, customer_id: int, cross_search: bool
    ) -> ToolCallResult:
        """Execute a single tool call."""
        try:
            request = HybridSearchRequest(
                query=query,
                customer_id=customer_id,
                cross_search=cross_search,
                limit=20
            )
            result = await self.search_service.search(request)
            
            return ToolCallResult(
                tool_name="hybrid_search",
                success=True,
                results=result.model_dump()
            )
        except Exception as e:
            logger.error(f"Tool call failed: {e}")
            return ToolCallResult(
                tool_name="hybrid_search",
                success=False,
                results=None,
                error=str(e)
            )

    async def _execute_fallback(
        self, query: str, customer_id: int
    ) -> Optional[ToolCallResult]:
        """Execute fallback search strategy."""
        try:
            cross_request = HybridSearchRequest(
                query=query,
                customer_id=customer_id,
                cross_search=True,
                limit=10
            )
            result = await self.search_service.cross_search(cross_request)
            
            if result.results:
                return ToolCallResult(
                    tool_name="cross_search",
                    success=True,
                    results=result.model_dump()
                )
        except Exception as e:
            logger.warning(f"Fallback search failed: {e}")
        
        return None

    def _is_sufficient(self, results: List[ToolCallResult]) -> bool:
        """Check if accumulated results are sufficient."""
        total_results = 0
        for result in results:
            if result.success and result.results:
                total_results += result.results.get("total", 0)
        
        return total_results >= 5

    async def generate_response(
        self, query: str, tool_results: List[ToolCallResult], customer_id: int
    ) -> str:
        """Generate final response using collected context."""
        context_parts = []
        
        for i, result in enumerate(tool_results, 1):
            if not result.success:
                continue
            
            context_parts.append(f"[Search {i}] Tool: {result.tool_name}")
            
            if result.results and result.results.get("results"):
                for item in result.results["results"][:3]:
                    context_parts.append(
                        f"  - {item.get('document_title', 'Untitled')}"
                    )
                    if item.get("content"):
                        context_parts.append(f"    {item['content'][:200]}...")
        
        context = "\n".join(context_parts) if context_parts else "No relevant documents found."
        
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"""Based on the following search results, answer the user's question.

User Question: {query}
Customer ID: {customer_id}

Search Results:
{context}

Generate a helpful response citing your sources. If no relevant information was found, say so clearly."""}
        ]
        
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.7,
            max_tokens=2000
        )
        
        return response.choices[0].message.content


class AdaptiveRAGOrchestrator:
    """Orchestrates the adaptive RAG pipeline."""
    
    def __init__(self, db_session):
        self.db = db_session
        self.agent = AgenticRAGAgent(db_session)

    async def process(self, query: str, customer_id: int, cross_search: bool = False) -> Dict[str, Any]:
        """Main entry point for adaptive RAG processing."""
        complexity = await self.agent.analyze_complexity(query)
        
        if not complexity.is_complex:
            single_result = await self.agent.single_pass_search(
                HybridSearchRequest(query=query, customer_id=customer_id, cross_search=cross_search)
            )
            
            if single_result["needs_escalation"]:
                tool_results = await self.agent.multi_step_search(query, customer_id, cross_search)
                response = await self.agent.generate_response(query, tool_results, customer_id)
                
                return {
                    "mode": "multi-step",
                    "response": response,
                    "tool_results": [r.model_dump() for r in tool_results],
                    "escalation_reason": "Low initial search confidence"
                }
            
            return {
                "mode": "single-pass",
                "response": await self._format_single_pass_response(single_result["search_results"], query),
                "tool_results": [],
                "escalation_reason": None
            }
        
        tool_results = await self.agent.multi_step_search(query, customer_id, cross_search)
        response = await self.agent.generate_response(query, tool_results, customer_id)
        
        return {
            "mode": "multi-step",
            "response": response,
            "tool_results": [r.model_dump() for r in tool_results],
            "escalation_reason": "Complex query detected"
        }

    async def _format_single_pass_response(self, search_result, query: str) -> str:
        """Format single-pass search results into a response."""
        if not search_result.results:
            return "검색 결과가 없습니다."
        
        parts = []
        for i, item in enumerate(search_result.results[:5], 1):
            parts.append(f"[{i}] {item.document_title}")
            if item.section_title:
                parts.append(f"   섹션: {item.section_title}")
            parts.append(f"   {item.content[:300]}...")
            parts.append("")
        
        return "\n".join(parts)
