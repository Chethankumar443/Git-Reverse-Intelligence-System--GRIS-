"""Tests for ContextCompiler."""

from __future__ import annotations

from typing import Any

import pytest

from git_reverse.ai.context import ContextCompiler
from git_reverse.storage.database import Database, Repository, RepositoryDAO, Node


@pytest.mark.asyncio
async def test_compile_context(db: Database) -> None:
    # 1. Register a repository in DB
    repo_dao = RepositoryDAO(db)
    await repo_dao.upsert(
        Repository(
            id="repo-ai-test",
            url="https://github.com/test/repo",
            name="test-repo",
            primary_language="python",
        )
    )

    # 2. Insert mock nodes
    await db.conn.execute(
        """
        INSERT INTO nodes (id, repo_id, type, name, file_path, start_line, end_line, content, metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "node-module-1",
            "repo-ai-test",
            "module",
            "main",
            "src/main.py",
            1,
            10,
            None,
            "{}",
        ),
    )
    await db.conn.execute(
        """
        INSERT INTO nodes (id, repo_id, type, name, file_path, start_line, end_line, content, metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "node-func-1",
            "repo-ai-test",
            "function",
            "calculate_sum",
            "src/main.py",
            3,
            8,
            "def calculate_sum(a, b):\n    return a + b",
            '{"complexity": 1, "loc": 2, "depth": 1}',
        ),
    )
    await db.conn.commit()

    # 3. Compile context without query
    compiler = ContextCompiler(db)
    context = await compiler.compile_context(repo_id="repo-ai-test")
    assert "test-repo" in context
    assert "python" in context
    assert "src/main.py" in context

    # 4. Compile context with query containing keyword match
    query_context = await compiler.compile_context(repo_id="repo-ai-test", query="calculate sum function")
    assert "calculate_sum" in query_context
    assert "def calculate_sum(a, b):" in query_context
    assert "complexity=1" in query_context
