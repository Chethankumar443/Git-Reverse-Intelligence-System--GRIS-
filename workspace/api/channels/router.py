"""Channels and messages router."""
import re
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import Optional

from database.db import get_db
from database.models import (
    Channel, Message, MessageType, MemberType,
    Agent, User, AuditEntry,
)
from auth.router import get_current_user
from auth.jwt import decode_token
from ws.manager import ws_manager

router = APIRouter()


# ──────────────── Helpers ────────────────

def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9-]", "", name.lower().replace(" ", "-"))[:64]


async def _get_caller(request: Request, db: AsyncSession) -> tuple:
    """Return (user|None, agent|None, member_type) from Authorization header."""
    auth = request.headers.get("Authorization", "")
    token = auth.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(401, "Missing Authorization header")
    payload = decode_token(token)
    if not payload:
        raise HTTPException(401, "Invalid token")

    if payload.get("type") == "agent":
        agent_id = payload["sub"]
        res = await db.execute(select(Agent).where(Agent.id == agent_id))
        agent = res.scalar_one_or_none()
        if not agent or not agent.is_active:
            raise HTTPException(401, "Agent not found or deactivated")
        return None, agent, MemberType.AGENT
    else:
        user_id = payload["sub"]
        res = await db.execute(select(User).where(User.id == user_id))
        user = res.scalar_one_or_none()
        if not user or not user.is_active:
            raise HTTPException(401, "User not found")
        return user, None, MemberType.HUMAN


# ──────────────── Schemas ────────────────

class ChannelCreate(BaseModel):
    name: str
    description: str | None = None
    is_private: bool = False


class ChannelOut(BaseModel):
    id: str
    name: str
    slug: str
    description: str | None
    is_private: bool
    created_at: datetime

    class Config:
        from_attributes = True


class MessageCreate(BaseModel):
    content: str
    message_type: MessageType = MessageType.TEXT
    metadata: dict = {}
    parent_id: str | None = None


class AuthorOut(BaseModel):
    id: str
    name: str
    type: str  # "human" | "agent"
    avatar_emoji: str | None = None
    avatar_url: str | None = None
    capabilities: list[str] = []


class MessageOut(BaseModel):
    id: str
    channel_id: str
    author: AuthorOut
    member_type: str
    message_type: str
    content: str
    metadata: dict
    parent_id: str | None
    created_at: datetime
    edited_at: datetime | None

    class Config:
        from_attributes = True


def _author_out(user: Optional[User], agent: Optional[Agent], mtype: MemberType) -> AuthorOut:
    if mtype == MemberType.AGENT and agent:
        return AuthorOut(
            id=agent.id,
            name=agent.name,
            type="agent",
            avatar_emoji=agent.avatar_emoji,
            capabilities=agent.capabilities or [],
        )
    return AuthorOut(
        id=user.id,
        name=user.display_name or user.username,
        type="human",
        avatar_url=user.avatar_url,
    )


def _msg_out(msg: Message) -> MessageOut:
    return MessageOut(
        id=msg.id,
        channel_id=msg.channel_id,
        author=_author_out(msg.author_user, msg.author_agent, msg.member_type),
        member_type=msg.member_type,
        message_type=msg.message_type,
        content=msg.content,
        metadata=msg.metadata_ or {},
        parent_id=msg.parent_id,
        created_at=msg.created_at,
        edited_at=msg.edited_at,
    )


# ──────────────── Channel Endpoints ────────────────

@router.post("/", response_model=ChannelOut, status_code=201)
async def create_channel(
    body: ChannelCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    slug = _slug(body.name)
    existing = await db.execute(select(Channel).where(Channel.slug == slug))
    if existing.scalar_one_or_none():
        raise HTTPException(400, f"Channel '{slug}' already exists")
    ch = Channel(
        name=body.name,
        slug=slug,
        description=body.description,
        is_private=body.is_private,
        created_by_id=current_user.id,
    )
    db.add(ch)
    await db.flush()
    await db.refresh(ch)
    return ChannelOut.model_validate(ch)


@router.get("/", response_model=list[ChannelOut])
async def list_channels(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(select(Channel).where(Channel.is_private.is_(False)))
    return [ChannelOut.model_validate(c) for c in result.scalars().all()]


# ──────────────── Message Endpoints ────────────────

@router.post("/{channel_id}/messages", response_model=MessageOut, status_code=201)
async def post_message(
    channel_id: str,
    body: MessageCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Post a message — works for both human users and AI agents."""
    user, agent, mtype = await _get_caller(request, db)

    res = await db.execute(select(Channel).where(Channel.id == channel_id))
    channel = res.scalar_one_or_none()
    if not channel:
        raise HTTPException(404, "Channel not found")

    msg = Message(
        channel_id=channel_id,
        author_user_id=user.id if user else None,
        author_agent_id=agent.id if agent else None,
        member_type=mtype,
        message_type=body.message_type,
        content=body.content,
        metadata_=body.metadata,
        parent_id=body.parent_id,
    )
    db.add(msg)

    # Audit log
    audit = AuditEntry(
        user_id=user.id if user else None,
        agent_id=agent.id if agent else None,
        member_type=mtype,
        action="post_message",
        resource_type="message",
        channel_id=channel_id,
        detail={"message_type": body.message_type, "content_len": len(body.content)},
    )
    db.add(audit)
    await db.flush()
    await db.refresh(msg)
    if user:
        await db.refresh(msg, ["author_user"])
    if agent:
        await db.refresh(msg, ["author_agent"])

    out = _msg_out(msg)
    # Broadcast to all WebSocket subscribers on this channel
    await ws_manager.broadcast(channel_id, out.model_dump(mode="json"))
    return out


@router.get("/{channel_id}/messages", response_model=list[MessageOut])
async def get_messages(
    channel_id: str,
    limit: int = 50,
    before_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = (
        select(Message)
        .where(Message.channel_id == channel_id, Message.is_deleted.is_(False))
        .order_by(desc(Message.created_at))
        .limit(limit)
    )
    result = await db.execute(q)
    msgs = list(reversed(result.scalars().all()))
    return [_msg_out(m) for m in msgs]
