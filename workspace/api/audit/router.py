"""Audit trail router."""
from datetime import datetime
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from database.db import get_db
from database.models import AuditEntry
from auth.router import get_current_user
from database.models import User

router = APIRouter()


class AuditEntryOut(BaseModel):
    id: str
    user_id: str | None
    agent_id: str | None
    member_type: str
    action: str
    resource_type: str | None
    resource_id: str | None
    channel_id: str | None
    detail: dict
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("/", response_model=list[AuditEntryOut])
async def get_audit_log(
    limit: int = Query(100, le=500),
    agent_id: str | None = None,
    channel_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.is_admin:
        from fastapi import HTTPException
        raise HTTPException(403, "Admin only")

    q = select(AuditEntry).order_by(desc(AuditEntry.created_at)).limit(limit)
    if agent_id:
        q = q.where(AuditEntry.agent_id == agent_id)
    if channel_id:
        q = q.where(AuditEntry.channel_id == channel_id)

    result = await db.execute(q)
    return [AuditEntryOut.model_validate(e) for e in result.scalars().all()]
