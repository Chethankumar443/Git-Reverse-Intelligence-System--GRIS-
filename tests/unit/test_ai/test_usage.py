"""Tests for UsageTracker."""

from __future__ import annotations

import pytest

from git_reverse.ai.usage import UsageTracker
from git_reverse.storage.database import Database, SessionDAO


@pytest.mark.asyncio
async def test_log_and_retrieve_stats(db: Database) -> None:
    session_dao = SessionDAO(db)
    session = await session_dao.create(model="openai/gpt-4o-mini")

    tracker = UsageTracker(db)
    # Log first request
    await tracker.log_request(
        session_id=session.id,
        model="openai/gpt-4o-mini",
        prompt_tokens=1000,
        completion_tokens=500,
        latency_ms=1200,
    )
    
    # Log second request
    await tracker.log_request(
        session_id=session.id,
        model="openai/gpt-4o-mini",
        prompt_tokens=2000,
        completion_tokens=1000,
        latency_ms=1800,
    )

    stats = await tracker.get_session_stats(session.id)
    assert stats["requests"] == 2
    assert stats["total_prompt_tokens"] == 3000
    assert stats["total_completion_tokens"] == 1500
    assert stats["avg_latency_ms"] == 1500.0
    
    # Cost for gpt-4o-mini: $0.15/1M prompt, $0.60/1M completion
    # Request 1 prompt cost: 1000 * 0.15 / 1M = 0.00015
    # Request 1 comp cost: 500 * 0.60 / 1M = 0.00030
    # Request 2 prompt cost: 2000 * 0.15 / 1M = 0.00030
    # Request 2 comp cost: 1000 * 0.60 / 1M = 0.00060
    # Total cost: 0.00015 + 0.00030 + 0.00030 + 0.00060 = 0.00135
    assert pytest.approx(stats["total_cost_usd"], abs=1e-6) == 0.00135
