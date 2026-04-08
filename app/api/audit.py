from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from datetime import datetime, timedelta

from app.core.database import get_db
from app.models.audit import AuditLog
from app.schemas.common import AuditLogResponse

router = APIRouter()


@router.get("/logs", response_model=List[AuditLogResponse])
async def list_audit_logs(
    customer_id: Optional[int] = None,
    user_id: Optional[str] = None,
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=1000),
    db: AsyncSession = Depends(get_db)
):
    query = select(AuditLog)
    
    if customer_id:
        query = query.where(AuditLog.customer_id == customer_id)
    if user_id:
        query = query.where(AuditLog.user_id == user_id)
    if action:
        query = query.where(AuditLog.action == action)
    if resource_type:
        query = query.where(AuditLog.resource_type == resource_type)
    if start_date:
        query = query.where(AuditLog.created_at >= start_date)
    if end_date:
        query = query.where(AuditLog.created_at <= end_date)
    
    query = query.offset(skip).limit(limit).order_by(AuditLog.created_at.desc())
    
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/logs/stats")
async def get_audit_stats(
    customer_id: Optional[int] = None,
    days: int = Query(7, ge=1, le=90),
    db: AsyncSession = Depends(get_db)
):
    from sqlalchemy import func
    
    start_date = datetime.utcnow() - timedelta(days=days)
    
    query = select(
        AuditLog.action,
        func.count(AuditLog.id).label("count")
    ).where(AuditLog.created_at >= start_date)
    
    if customer_id:
        query = query.where(AuditLog.customer_id == customer_id)
    
    query = query.group_by(AuditLog.action)
    
    result = await db.execute(query)
    stats = result.all()
    
    return {
        "period_days": days,
        "actions": {row.action: row.count for row in stats},
        "total": sum(row.count for row in stats)
    }
