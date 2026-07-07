"""Tests for AnalysisPipeline."""

from __future__ import annotations

from pathlib import Path
from collections.abc import AsyncGenerator

import pytest

from typing import Any

from git_reverse.analysis.pipeline import AnalysisPipeline
from git_reverse.core.events import EventBus
from git_reverse.ingestion.validator import RepositoryValidator
from git_reverse.storage.database import Database, Repository, RepositoryDAO


@pytest.mark.asyncio
async def test_pipeline_integration(
    make_git_repo: Any,
    db: Database,
    event_bus: EventBus,
) -> None:
    # 1. Create a mock python repository
    code = """
def process_data(x):
    if x > 0:
        return x * 2
    return 0
"""
    repo_path = make_git_repo(
        "pipeline-repo",
        files={
            "src/main.py": code,
        },
    )

    # 1.5 Register repository in the database to satisfy FK constraints
    repo_dao = RepositoryDAO(db)
    await repo_dao.upsert(
        Repository(
            id="repo-pipeline-test",
            url=str(repo_path),
            name="pipeline-repo",
            analysis_status="pending",
        )
    )

    # 2. Run validator
    validator = RepositoryValidator()
    val_result = validator.validate(repo_path)

    # 3. Execute analysis pipeline
    pipeline = AnalysisPipeline(db=db, bus=event_bus)
    
    progress_states = []
    async def progress_cb(phase: str, completed: int, total: int, msg: str) -> None:
        progress_states.append(phase)

    await pipeline.run(
        repo_id="repo-pipeline-test",
        validation_result=val_result,
        progress_callback=progress_cb,
    )

    # 4. Verify SQLite databases matches generated assets
    assert "complete" in progress_states
    
    # Query database nodes
    async with db.conn.execute("SELECT * FROM nodes WHERE repo_id = 'repo-pipeline-test'") as cursor:
        nodes = list(await cursor.fetchall())
    
    assert len(nodes) >= 2  # module node + function node
    
    node_types = {n["type"] for n in nodes}
    assert "module" in node_types
    assert "function" in node_types

    # Verify complexity metric was populated in node metadata
    fn_node = [n for n in nodes if n["type"] == "function"][0]
    import json
    meta = json.loads(fn_node["metadata"])
    assert "complexity" in meta
    assert meta["complexity"] == 2  # base 1 + "if" branch = 2
