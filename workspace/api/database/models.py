"""Database models — users, agents, channels, messages, audit log."""
import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import (
    Column, String, Text, DateTime, Boolean, ForeignKey,
    Enum, Integer, JSON,
)
from sqlalchemy.orm import relationship, DeclarativeBase


class Base(DeclarativeBase):
    pass


def _uuid() -> str:
    return str(uuid.uuid4())


class MemberType(str, PyEnum):
    HUMAN = "human"
    AGENT = "agent"


class AgentCapability(str, PyEnum):
    READ_CHANNELS = "read_channels"
    POST_MESSAGES = "post_messages"
    REVIEW_PATCHES = "review_patches"
    TRIAGE_ISSUES = "triage_issues"
    QUERY_KB = "query_kb"
    RUN_ANALYSIS = "run_analysis"
    MANAGE_AGENTS = "manage_agents"


# ─────────────────── Users ───────────────────

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=_uuid)
    username = Column(String(64), unique=True, nullable=False, index=True)
    email = Column(String(256), unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    display_name = Column(String(128))
    avatar_url = Column(String(512))
    is_admin = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_seen_at = Column(DateTime, default=datetime.utcnow)

    messages = relationship("Message", back_populates="author_user",
                            foreign_keys="Message.author_user_id")
    audit_entries = relationship("AuditEntry", back_populates="user",
                                 foreign_keys="AuditEntry.user_id")


# ─────────────────── Agents ───────────────────

class Agent(Base):
    __tablename__ = "agents"

    id = Column(String, primary_key=True, default=_uuid)
    name = Column(String(128), nullable=False)
    slug = Column(String(64), unique=True, nullable=False, index=True)
    description = Column(Text)
    avatar_emoji = Column(String(8), default="🤖")
    # Stored as JSON list of AgentCapability values
    capabilities = Column(JSON, default=list)
    llm_provider = Column(String(128))          # e.g. "openrouter"
    llm_model = Column(String(256))             # e.g. "cohere/command-r"
    system_prompt = Column(Text)
    token_hash = Column(String, nullable=False)  # hashed agent API token
    is_active = Column(Boolean, default=True)
    created_by_id = Column(String, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    last_active_at = Column(DateTime, default=datetime.utcnow)

    created_by = relationship("User", foreign_keys=[created_by_id])
    messages = relationship("Message", back_populates="author_agent",
                            foreign_keys="Message.author_agent_id")
    audit_entries = relationship("AuditEntry", back_populates="agent",
                                 foreign_keys="AuditEntry.agent_id")


# ─────────────────── Channels ───────────────────

class Channel(Base):
    __tablename__ = "channels"

    id = Column(String, primary_key=True, default=_uuid)
    name = Column(String(128), nullable=False, index=True)
    slug = Column(String(64), unique=True, nullable=False)
    description = Column(Text)
    is_private = Column(Boolean, default=False)
    created_by_id = Column(String, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)

    created_by = relationship("User", foreign_keys=[created_by_id])
    messages = relationship("Message", back_populates="channel",
                            cascade="all, delete-orphan")


class MessageType(str, PyEnum):
    TEXT = "text"
    CODE_SNIPPET = "code_snippet"
    KB_EXCERPT = "kb_excerpt"
    PATCH_REVIEW = "patch_review"
    SYSTEM_EVENT = "system_event"
    AGENT_ACTION = "agent_action"


class Message(Base):
    __tablename__ = "messages"

    id = Column(String, primary_key=True, default=_uuid)
    channel_id = Column(String, ForeignKey("channels.id"), nullable=False, index=True)
    # Exactly one of these is set
    author_user_id = Column(String, ForeignKey("users.id"), nullable=True)
    author_agent_id = Column(String, ForeignKey("agents.id"), nullable=True)
    member_type = Column(Enum(MemberType), nullable=False)
    message_type = Column(Enum(MessageType), default=MessageType.TEXT)
    content = Column(Text, nullable=False)
    metadata_ = Column("metadata", JSON, default=dict)  # extra payload for code/kb/patch
    parent_id = Column(String, ForeignKey("messages.id"), nullable=True)  # thread
    is_deleted = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    edited_at = Column(DateTime, nullable=True)

    channel = relationship("Channel", back_populates="messages")
    author_user = relationship("User", back_populates="messages",
                               foreign_keys=[author_user_id])
    author_agent = relationship("Agent", back_populates="messages",
                                foreign_keys=[author_agent_id])
    replies = relationship("Message", backref="parent",
                           foreign_keys=[parent_id])


# ─────────────────── Audit Trail ───────────────────

class AuditEntry(Base):
    __tablename__ = "audit_entries"

    id = Column(String, primary_key=True, default=_uuid)
    # Exactly one of these is set
    user_id = Column(String, ForeignKey("users.id"), nullable=True)
    agent_id = Column(String, ForeignKey("agents.id"), nullable=True)
    member_type = Column(Enum(MemberType), nullable=False)
    action = Column(String(128), nullable=False)          # e.g. "post_message"
    resource_type = Column(String(64))                    # e.g. "channel", "agent"
    resource_id = Column(String)
    channel_id = Column(String, ForeignKey("channels.id"), nullable=True)
    detail = Column(JSON, default=dict)                   # contextual payload
    ip_address = Column(String(64))
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    user = relationship("User", back_populates="audit_entries",
                        foreign_keys=[user_id])
    agent = relationship("Agent", back_populates="audit_entries",
                         foreign_keys=[agent_id])
