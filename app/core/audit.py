from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import insert
from app.core.database import AsyncSessionLocal
from app.models.audit import AuditLog
from app.models.enums import AuditAction
import json
import logging
from typing import Callable, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


AUDITED_PATHS = {
    "POST:/api/v1/documents": AuditAction.DOCUMENT_UPLOAD,
    "GET:/api/v1/documents": AuditAction.DOCUMENT_VIEW,
    "POST:/api/v1/search": AuditAction.SEARCH,
    "POST:/api/v1/chat": AuditAction.CHAT_REQUEST,
    "POST:/api/v1/chat/enrich-event": AuditAction.ENRICH_REQUEST,
    "GET:/api/v1/events": AuditAction.EVENT_VIEW,
    "GET:/api/v1/audit/logs": AuditAction.SEARCH,
    "POST:/api/v1/incident/webhook": AuditAction.EVENT_VIEW,
    "GET:/api/v1/incident/dashboard": AuditAction.EVENT_VIEW,
    "GET:/api/v1/incident/events": AuditAction.EVENT_VIEW,
    "POST:/api/v1/incident/events": AuditAction.CHAT_REQUEST,
    "GET:/api/v1/incident/events/": AuditAction.EVENT_VIEW,
}


class AuditMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path
        method = request.method
        action_key = f"{method}:{path}"
        
        customer_id = self._extract_customer_id(request)
        user_id = self._get_user_id(request)
        
        response = await call_next(request)
        
        action = self._match_action(action_key)
        if action:
            await self._log_audit(
                customer_id=customer_id,
                user_id=user_id,
                action=action,
                request=request,
                response=response
            )
        
        return response

    def _extract_customer_id(self, request: Request) -> Optional[int]:
        if hasattr(request.state, "customer_id"):
            return request.state.customer_id
        
        body = request._body
        if body:
            try:
                data = json.loads(body)
                return data.get("customer_id")
            except:
                pass
        
        customer_id = request.query_params.get("customer_id")
        if customer_id:
            return int(customer_id)
        
        return None

    def _get_user_id(self, request: Request) -> Optional[str]:
        if hasattr(request.state, "user_id"):
            return request.state.user_id
        
        auth_header = request.headers.get("Authorization")
        if auth_header:
            return auth_header[:50]
        
        return request.client.host if request.client else None

    def _match_action(self, action_key: str) -> Optional[AuditAction]:
        for pattern, action in AUDITED_PATHS.items():
            if action_key.startswith(pattern.replace("/api/v1", "")):
                return action
        
        for pattern, action in AUDITED_PATHS.items():
            if pattern.endswith("*") and action_key.startswith(pattern[:-1]):
                return action
        
        return None

    async def _log_audit(
        self,
        customer_id: Optional[int],
        user_id: Optional[str],
        action: AuditAction,
        request: Request,
        response: Response
    ):
        try:
            async with AsyncSessionLocal() as db:
                body_text = None
                try:
                    body = request._body
                    if body:
                        body_text = body[:5000].decode("utf-8", errors="ignore")
                except:
                    pass
                
                audit_entry = AuditLog(
                    customer_id=customer_id,
                    user_id=user_id,
                    action=action.value,
                    request_path=str(request.url.path),
                    request_method=request.method,
                    request_body_json=body_text,
                    response_status_code=response.status_code,
                    ip_address=request.client.host if request.client else None,
                    user_agent=request.headers.get("User-Agent"),
                )
                
                db.add(audit_entry)
                await db.commit()
                
        except Exception as e:
            logger.error(f"Audit logging failed: {e}")


async def create_audit_log(
    customer_id: Optional[int],
    user_id: Optional[str],
    action: AuditAction,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    metadata: Optional[dict] = None
) -> int:
    async with AsyncSessionLocal() as db:
        audit_entry = AuditLog(
            customer_id=customer_id,
            user_id=user_id,
            action=action.value,
            resource_type=resource_type,
            resource_id=resource_id,
            metadata_json=json.dumps(metadata) if metadata else None,
        )
        db.add(audit_entry)
        await db.commit()
        await db.refresh(audit_entry)
        return audit_entry.id
