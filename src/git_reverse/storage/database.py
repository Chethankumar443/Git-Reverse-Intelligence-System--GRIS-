"""
Async SQLite database layer using aiosqlite.

Architecture:
  - `Database` manages the connection lifecycle, migrations, and provides
    low-level query helpers.
  - Higher-level repositories (SessionRepository, NodeRepository, etc.) sit on
    top and own their own SQL — no raw SQL leaks into business logic.
  - All public methods are async to avoid blocking the Textual event loop.
  - WAL mode is enabled for concurrent read performance.
"""

from __future__ import annotations

import importlib.resources
import json
import sqlite3
import uuid
from contextlib import asynccontextmanager
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, AsyncGenerator

import aiosqlite

from git_reverse.core.exceptions import DatabaseError, SessionNotFoundError
from git_reverse.core.logging import get_logger

log = get_logger(__name__)

# Path to the migrations directory bundled with the package
_MIGRATIONS_DIR = Path(__file__).parent / "migrations"


# ── Helper: session ID generator ──────────────────────────────────────────────
def generate_session_id() -> str:
    """Generate a human-readable session ID: GR-YYYYMMDD-XXXX."""
    now = datetime.now(tz=UTC)
    suffix = uuid.uuid4().hex[:6].upper()
    return f"GR-{now.strftime('%Y%m%d')}-{suffix}"


# ── Data Models (lightweight dataclasses, no ORM overhead) ────────────────────
@dataclass
class Repository:
    id: str
    url: str
    name: str
    local_path: str | None = None
    primary_language: str | None = None
    size_bytes: int = 0
    cloned_at: str | None = None
    last_analyzed_at: str | None = None
    analysis_status: str = "pending"
    error_message: str | None = None
    metadata: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        if self.metadata is None:
            self.metadata = {}


@dataclass
class Session:
    id: str
    mode: str
    model: str
    repo_id: str | None = None
    username: str | None = None
    summary: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    is_archived: bool = False


@dataclass
class Message:
    id: str
    session_id: str
    role: str  # 'user' | 'assistant' | 'system'
    content: str
    model: str | None = None
    tokens_used: int | None = None
    created_at: str | None = None


@dataclass
class Node:
    id: str
    repo_id: str
    type: str
    name: str
    file_path: str | None = None
    start_line: int | None = None
    end_line: int | None = None
    content: str | None = None
    metadata: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        if self.metadata is None:
            self.metadata = {}


@dataclass
class Edge:
    source_id: str
    target_id: str
    relation_type: str
    metadata: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        if self.metadata is None:
            self.metadata = {}


# ── Database ──────────────────────────────────────────────────────────────────
class Database:
    """
    Async SQLite database manager.

    Lifecycle:
        db = Database(path)
        await db.connect()          # Opens the connection, runs migrations
        ...
        await db.close()            # Closes gracefully

    Or use the async context manager:
        async with Database(path) as db:
            ...
    """

    def __init__(self, db_path: Path) -> None:
        self._path = db_path
        self._conn: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        """Open the database connection and apply any pending migrations."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._conn = await aiosqlite.connect(self._path)
            self._conn.row_factory = aiosqlite.Row
            await self._configure_pragmas()
            await self._run_migrations()
            log.info("database_connected", path=str(self._path))
        except sqlite3.Error as exc:
            raise DatabaseError("connect", str(exc)) from exc

    async def close(self) -> None:
        """Close the database connection gracefully."""
        if self._conn:
            await self._conn.close()
            self._conn = None
            log.info("database_closed")

    async def __aenter__(self) -> "Database":
        await self.connect()
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()

    @property
    def conn(self) -> aiosqlite.Connection:
        """Return the live connection, raising if not connected."""
        if self._conn is None:
            raise DatabaseError("access", "Database is not connected. Call connect() first.")
        return self._conn

    @asynccontextmanager
    async def transaction(self) -> AsyncGenerator[aiosqlite.Connection, None]:
        """Context manager that wraps operations in a SQLite transaction."""
        async with self.conn.execute("BEGIN"):
            pass
        try:
            yield self.conn
            await self.conn.commit()
        except Exception:
            await self.conn.rollback()
            raise

    # ── Private helpers ───────────────────────────────────────────────────────
    async def _configure_pragmas(self) -> None:
        pragmas = [
            "PRAGMA journal_mode = WAL",
            "PRAGMA foreign_keys = ON",
            "PRAGMA synchronous = NORMAL",
            "PRAGMA cache_size = -64000",  # 64 MB page cache
            "PRAGMA temp_store = MEMORY",
        ]
        for pragma in pragmas:
            await self.conn.execute(pragma)
        await self.conn.commit()

    async def _run_migrations(self) -> None:
        """Apply SQL migration files in order, skipping already-applied ones."""
        await self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version     INTEGER PRIMARY KEY,
                applied_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
            )
            """
        )
        await self.conn.commit()

        async with self.conn.execute(
            "SELECT version FROM schema_migrations"
        ) as cursor:
            applied: set[int] = {row[0] for row in await cursor.fetchall()}

        migration_files = sorted(_MIGRATIONS_DIR.glob("*.sql"))
        for migration_file in migration_files:
            version_str = migration_file.name.split("_")[0]
            version = int(version_str)
            if version in applied:
                continue
            sql = migration_file.read_text(encoding="utf-8")
            await self.conn.executescript(sql)
            await self.conn.execute(
                "INSERT OR IGNORE INTO schema_migrations (version) VALUES (?)", (version,)
            )
            await self.conn.commit()
            log.info("migration_applied", version=version, file=migration_file.name)


# ── Repository DAO ────────────────────────────────────────────────────────────
class RepositoryDAO:
    """Data Access Object for Repository records."""

    def __init__(self, db: Database) -> None:
        self._db = db

    async def upsert(self, repo: Repository) -> Repository:
        """Insert or replace a repository record."""
        meta_json = json.dumps(repo.metadata or {})
        try:
            await self._db.conn.execute(
                """
                INSERT INTO repositories
                    (id, url, name, local_path, primary_language, size_bytes,
                     cloned_at, last_analyzed_at, analysis_status, error_message, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    local_path        = excluded.local_path,
                    primary_language  = excluded.primary_language,
                    size_bytes        = excluded.size_bytes,
                    cloned_at         = excluded.cloned_at,
                    last_analyzed_at  = excluded.last_analyzed_at,
                    analysis_status   = excluded.analysis_status,
                    error_message     = excluded.error_message,
                    metadata          = excluded.metadata
                """,
                (
                    repo.id, repo.url, repo.name, repo.local_path,
                    repo.primary_language, repo.size_bytes, repo.cloned_at,
                    repo.last_analyzed_at, repo.analysis_status,
                    repo.error_message, meta_json,
                ),
            )
            await self._db.conn.commit()
        except sqlite3.Error as exc:
            raise DatabaseError("upsert_repository", str(exc)) from exc
        return repo

    async def get_by_id(self, repo_id: str) -> Repository | None:
        """Return a repository by its ID, or None if not found."""
        try:
            async with self._db.conn.execute(
                "SELECT * FROM repositories WHERE id = ?", (repo_id,)
            ) as cursor:
                row = await cursor.fetchone()
        except sqlite3.Error as exc:
            raise DatabaseError("get_repository_by_id", str(exc)) from exc
        if row is None:
            return None
        return self._row_to_repo(row)

    async def get_by_url(self, url: str) -> Repository | None:
        """Return the most recently analyzed repository matching a URL."""
        try:
            async with self._db.conn.execute(
                "SELECT * FROM repositories WHERE url = ? ORDER BY last_analyzed_at DESC LIMIT 1",
                (url,),
            ) as cursor:
                row = await cursor.fetchone()
        except sqlite3.Error as exc:
            raise DatabaseError("get_repository_by_url", str(exc)) from exc
        return self._row_to_repo(row) if row else None

    async def list_all(self, limit: int = 50) -> list[Repository]:
        """List repositories ordered by most recently analyzed."""
        try:
            async with self._db.conn.execute(
                "SELECT * FROM repositories ORDER BY last_analyzed_at DESC NULLS LAST LIMIT ?",
                (limit,),
            ) as cursor:
                return [self._row_to_repo(row) for row in await cursor.fetchall()]
        except sqlite3.Error as exc:
            raise DatabaseError("list_repositories", str(exc)) from exc

    async def update_status(
        self, repo_id: str, status: str, *, error: str | None = None
    ) -> None:
        """Update analysis_status and optionally set an error message."""
        try:
            await self._db.conn.execute(
                """
                UPDATE repositories
                SET analysis_status = ?, error_message = ?
                WHERE id = ?
                """,
                (status, error, repo_id),
            )
            await self._db.conn.commit()
        except sqlite3.Error as exc:
            raise DatabaseError("update_repository_status", str(exc)) from exc

    @staticmethod
    def _row_to_repo(row: aiosqlite.Row) -> Repository:
        d = dict(row)
        d["metadata"] = json.loads(d.get("metadata") or "{}")
        return Repository(**d)


# ── Session DAO ───────────────────────────────────────────────────────────────
class SessionDAO:
    """Data Access Object for Session records."""

    def __init__(self, db: Database) -> None:
        self._db = db

    async def create(
        self,
        *,
        model: str,
        mode: str = "explore",
        repo_id: str | None = None,
        username: str | None = None,
    ) -> Session:
        """Create and persist a new session, returning the populated model."""
        session = Session(
            id=generate_session_id(),
            mode=mode,
            model=model,
            repo_id=repo_id,
            username=username,
        )
        try:
            await self._db.conn.execute(
                """
                INSERT INTO sessions (id, repo_id, mode, model, username)
                VALUES (?, ?, ?, ?, ?)
                """,
                (session.id, session.repo_id, session.mode, session.model, session.username),
            )
            await self._db.conn.commit()
        except sqlite3.Error as exc:
            raise DatabaseError("create_session", str(exc)) from exc
        log.info("session_created", session_id=session.id, mode=mode, model=model)
        return session

    async def get_by_id(self, session_id: str) -> Session:
        """Return a session by ID or raise SessionNotFoundError."""
        try:
            async with self._db.conn.execute(
                "SELECT * FROM sessions WHERE id = ?", (session_id,)
            ) as cursor:
                row = await cursor.fetchone()
        except sqlite3.Error as exc:
            raise DatabaseError("get_session", str(exc)) from exc
        if row is None:
            raise SessionNotFoundError(session_id)
        return self._row_to_session(row)

    async def list_recent(self, limit: int = 20, *, include_archived: bool = False) -> list[Session]:
        """Return the most recently updated sessions."""
        query = "SELECT * FROM sessions"
        params: list[Any] = []
        if not include_archived:
            query += " WHERE is_archived = 0"
        query += " ORDER BY updated_at DESC LIMIT ?"
        params.append(limit)
        try:
            async with self._db.conn.execute(query, params) as cursor:
                return [self._row_to_session(row) for row in await cursor.fetchall()]
        except sqlite3.Error as exc:
            raise DatabaseError("list_sessions", str(exc)) from exc

    async def update_summary(self, session_id: str, summary: str) -> None:
        """Persist an LLM-generated session summary."""
        try:
            await self._db.conn.execute(
                """
                UPDATE sessions
                SET summary = ?,
                    updated_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now')
                WHERE id = ?
                """,
                (summary, session_id),
            )
            await self._db.conn.commit()
        except sqlite3.Error as exc:
            raise DatabaseError("update_session_summary", str(exc)) from exc

    async def archive(self, session_id: str) -> None:
        """Mark a session as archived (soft-delete)."""
        try:
            await self._db.conn.execute(
                "UPDATE sessions SET is_archived = 1 WHERE id = ?", (session_id,)
            )
            await self._db.conn.commit()
        except sqlite3.Error as exc:
            raise DatabaseError("archive_session", str(exc)) from exc

    @staticmethod
    def _row_to_session(row: aiosqlite.Row) -> Session:
        d = dict(row)
        d["is_archived"] = bool(d.get("is_archived", 0))
        return Session(**d)


# ── Message DAO ───────────────────────────────────────────────────────────────
class MessageDAO:
    """Data Access Object for conversation Message records."""

    def __init__(self, db: Database) -> None:
        self._db = db

    async def append(
        self,
        *,
        session_id: str,
        role: str,
        content: str,
        model: str | None = None,
        tokens_used: int | None = None,
    ) -> Message:
        """Append a message to a session's conversation history."""
        msg = Message(
            id=str(uuid.uuid4()),
            session_id=session_id,
            role=role,
            content=content,
            model=model,
            tokens_used=tokens_used,
        )
        try:
            await self._db.conn.execute(
                """
                INSERT INTO messages (id, session_id, role, content, model, tokens_used)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (msg.id, msg.session_id, msg.role, msg.content, msg.model, msg.tokens_used),
            )
            await self._db.conn.execute(
                "UPDATE sessions SET updated_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now') WHERE id = ?",
                (session_id,),
            )
            await self._db.conn.commit()
        except sqlite3.Error as exc:
            raise DatabaseError("append_message", str(exc)) from exc
        return msg

    async def get_history(self, session_id: str, *, limit: int = 100) -> list[Message]:
        """Return messages for a session, oldest first, up to `limit`."""
        try:
            async with self._db.conn.execute(
                "SELECT * FROM messages WHERE session_id = ? ORDER BY created_at ASC LIMIT ?",
                (session_id, limit),
            ) as cursor:
                return [Message(**dict(row)) for row in await cursor.fetchall()]
        except sqlite3.Error as exc:
            raise DatabaseError("get_message_history", str(exc)) from exc
