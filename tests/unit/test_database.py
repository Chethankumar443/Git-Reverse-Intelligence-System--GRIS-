"""
Tests for the async SQLite database layer — Database connection lifecycle,
migrations, and all DAO operations.
"""

from __future__ import annotations

import pytest

from git_reverse.core.exceptions import DatabaseError, SessionNotFoundError
from git_reverse.storage.database import (
    Database,
    MessageDAO,
    Repository,
    RepositoryDAO,
    Session,
    SessionDAO,
    generate_session_id,
)


# ── Session ID format ─────────────────────────────────────────────────────────
class TestGenerateSessionId:
    def test_format(self) -> None:
        sid = generate_session_id()
        assert sid.startswith("GR-")
        parts = sid.split("-")
        assert len(parts) == 3
        assert len(parts[1]) == 8   # YYYYMMDD
        assert len(parts[2]) == 6   # hex suffix

    def test_uniqueness(self) -> None:
        ids = {generate_session_id() for _ in range(100)}
        assert len(ids) == 100


# ── Database connection ───────────────────────────────────────────────────────
class TestDatabase:
    async def test_connects_and_migrates(self, db: Database) -> None:
        """Database fixture should connect without error and apply migrations."""
        # A simple query that requires the schema to exist
        async with db.conn.execute(
            "SELECT version FROM schema_migrations ORDER BY version"
        ) as cursor:
            rows = list(await cursor.fetchall())
        assert len(rows) >= 1
        assert rows[0][0] == 1

    async def test_migrations_are_idempotent(self, db: Database) -> None:
        """Connecting to an already-migrated DB must not raise or duplicate rows."""
        async with db.conn.execute(
            "SELECT COUNT(*) FROM schema_migrations"
        ) as cursor:
            row = await cursor.fetchone()
        assert row is not None
        count_before = row[0]

        # Simulating a second connection to the same path
        db2 = Database(db._path)
        await db2.connect()
        await db2.close()

        async with db.conn.execute(
            "SELECT COUNT(*) FROM schema_migrations"
        ) as cursor:
            row = await cursor.fetchone()
        assert row is not None
        assert row[0] == count_before


# ── RepositoryDAO ─────────────────────────────────────────────────────────────
class TestRepositoryDAO:
    async def test_upsert_and_get(self, db: Database) -> None:
        dao = RepositoryDAO(db)
        repo = Repository(
            id="repo-001",
            url="https://github.com/test/repo",
            name="repo",
            analysis_status="pending",
        )
        await dao.upsert(repo)
        fetched = await dao.get_by_id("repo-001")
        assert fetched is not None
        assert fetched.url == "https://github.com/test/repo"
        assert fetched.name == "repo"

    async def test_upsert_updates_existing(self, db: Database) -> None:
        dao = RepositoryDAO(db)
        repo = Repository(id="repo-002", url="https://github.com/x/y", name="y")
        await dao.upsert(repo)
        repo.analysis_status = "complete"
        repo.primary_language = "Python"
        await dao.upsert(repo)
        fetched = await dao.get_by_id("repo-002")
        assert fetched is not None
        assert fetched.analysis_status == "complete"
        assert fetched.primary_language == "Python"

    async def test_get_by_id_returns_none_for_missing(self, db: Database) -> None:
        dao = RepositoryDAO(db)
        result = await dao.get_by_id("nonexistent")
        assert result is None

    async def test_get_by_url(self, db: Database) -> None:
        dao = RepositoryDAO(db)
        repo = Repository(id="repo-003", url="https://github.com/a/b", name="b")
        await dao.upsert(repo)
        fetched = await dao.get_by_url("https://github.com/a/b")
        assert fetched is not None
        assert fetched.id == "repo-003"

    async def test_list_all(self, db: Database) -> None:
        dao = RepositoryDAO(db)
        for i in range(5):
            await dao.upsert(
                Repository(id=f"list-{i}", url=f"https://github.com/u/r{i}", name=f"r{i}")
            )
        repos = await dao.list_all()
        assert len(repos) >= 5

    async def test_update_status(self, db: Database) -> None:
        dao = RepositoryDAO(db)
        await dao.upsert(Repository(id="repo-status", url="u", name="u"))
        await dao.update_status("repo-status", "failed", error="timeout")
        fetched = await dao.get_by_id("repo-status")
        assert fetched is not None
        assert fetched.analysis_status == "failed"
        assert fetched.error_message == "timeout"

    async def test_metadata_roundtrip(self, db: Database) -> None:
        """JSON metadata must survive a write → read cycle unchanged."""
        dao = RepositoryDAO(db)
        meta = {"frameworks": ["fastapi", "sqlalchemy"], "stars": 1234}
        repo = Repository(id="repo-meta", url="u", name="u", metadata=meta)
        await dao.upsert(repo)
        fetched = await dao.get_by_id("repo-meta")
        assert fetched is not None
        assert fetched.metadata == meta


# ── SessionDAO ────────────────────────────────────────────────────────────────
class TestSessionDAO:
    async def test_create_returns_session(self, db: Database) -> None:
        dao = SessionDAO(db)
        session = await dao.create(model="gpt-4o-mini", mode="explore")
        assert session.id.startswith("GR-")
        assert session.mode == "explore"
        assert session.model == "gpt-4o-mini"

    async def test_get_by_id(self, db: Database) -> None:
        dao = SessionDAO(db)
        session = await dao.create(model="gpt-4o-mini")
        fetched = await dao.get_by_id(session.id)
        assert fetched.id == session.id

    async def test_get_by_id_raises_for_missing(self, db: Database) -> None:
        dao = SessionDAO(db)
        with pytest.raises(SessionNotFoundError):
            await dao.get_by_id("GR-00000000-ZZZZ")

    async def test_list_recent(self, db: Database) -> None:
        dao = SessionDAO(db)
        for _ in range(3):
            await dao.create(model="m")
        sessions = await dao.list_recent(limit=10)
        assert len(sessions) >= 3

    async def test_archive(self, db: Database) -> None:
        dao = SessionDAO(db)
        session = await dao.create(model="m")
        await dao.archive(session.id)
        active = await dao.list_recent(include_archived=False)
        assert all(s.id != session.id for s in active)

    async def test_update_summary(self, db: Database) -> None:
        dao = SessionDAO(db)
        session = await dao.create(model="m")
        await dao.update_summary(session.id, "A Python FastAPI project.")
        fetched = await dao.get_by_id(session.id)
        assert fetched.summary == "A Python FastAPI project."


# ── MessageDAO ────────────────────────────────────────────────────────────────
class TestMessageDAO:
    async def test_append_and_get_history(self, db: Database) -> None:
        session_dao = SessionDAO(db)
        message_dao = MessageDAO(db)
        session = await session_dao.create(model="m")

        await message_dao.append(session_id=session.id, role="user", content="Hello!")
        await message_dao.append(
            session_id=session.id, role="assistant", content="Hi there!", tokens_used=42
        )
        history = await message_dao.get_history(session.id)
        assert len(history) == 2
        assert history[0].role == "user"
        assert history[1].role == "assistant"
        assert history[1].tokens_used == 42

    async def test_history_is_chronological(self, db: Database) -> None:
        session_dao = SessionDAO(db)
        message_dao = MessageDAO(db)
        session = await session_dao.create(model="m")
        for i in range(5):
            await message_dao.append(session_id=session.id, role="user", content=str(i))
        history = await message_dao.get_history(session.id)
        contents = [int(m.content) for m in history]
        assert contents == sorted(contents)
