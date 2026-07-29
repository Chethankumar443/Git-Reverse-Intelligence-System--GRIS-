"""Agents router: create agents, manage capabilities, issue agent tokens."""
import secrets
import hashlib
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database.db import get_db
from database.models import Agent, AgentCapability
from auth.router import get_current_user
from auth.jwt import create_agent_token, hash_password
from database.models import User

router = APIRouter()


# ──────────────── Schemas ────────────────

class AgentCreate(BaseModel):
    name: str
    slug: str
    description: str | None = None
    avatar_emoji: str = "🤖"
    capabilities: list[str] = [AgentCapability.READ_CHANNELS, AgentCapability.POST_MESSAGES]
    llm_provider: str | None = None
    llm_model: str | None = None
    system_prompt: str | None = None


class AgentOut(BaseModel):
    id: str
    name: str
    slug: str
    description: str | None
    avatar_emoji: str
    capabilities: list[str]
    llm_provider: str | None
    llm_model: str | None
    is_active: bool
    created_at: datetime
    last_active_at: datetime

    class Config:
        from_attributes = True


class AgentTokenResponse(BaseModel):
    agent_id: str
    token: str
    capabilities: list[str]
    warning: str = "Store this token securely — it will not be shown again."


# ──────────────── Endpoints ────────────────

@router.post("/", response_model=AgentTokenResponse, status_code=201)
async def create_agent(
    body: AgentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create an AI agent identity. Returns a one-time token; hash stored in DB."""
    existing = await db.execute(select(Agent).where(Agent.slug == body.slug))
    if existing.scalar_one_or_none():
        raise HTTPException(400, f"Agent slug '{body.slug}' already taken")

    # Generate a secure token
    raw_token = secrets.token_urlsafe(48)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

    agent = Agent(
        name=body.name,
        slug=body.slug,
        description=body.description,
        avatar_emoji=body.avatar_emoji,
        capabilities=body.capabilities,
        llm_provider=body.llm_provider,
        llm_model=body.llm_model,
        system_prompt=body.system_prompt,
        token_hash=token_hash,
        created_by_id=current_user.id,
    )
    db.add(agent)
    await db.flush()
    await db.refresh(agent)

    # Build a JWT embedding the agent ID and capabilities
    jwt_token = create_agent_token(agent.id, body.capabilities)

    return AgentTokenResponse(
        agent_id=agent.id,
        token=jwt_token,
        capabilities=body.capabilities,
    )


@router.get("/", response_model=list[AgentOut])
async def list_agents(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(select(Agent).where(Agent.is_active.is_(True)))
    return [AgentOut.model_validate(a) for a in result.scalars().all()]


@router.get("/{slug}", response_model=AgentOut)
async def get_agent(
    slug: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(select(Agent).where(Agent.slug == slug))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(404, f"Agent '{slug}' not found")
    return AgentOut.model_validate(agent)


@router.patch("/{slug}/deactivate")
async def deactivate_agent(
    slug: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.is_admin:
        raise HTTPException(403, "Only admins can deactivate agents")
    result = await db.execute(select(Agent).where(Agent.slug == slug))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(404, "Agent not found")
    agent.is_active = False
    return {"status": "deactivated"}
