"""
Usage and Token tracker.

Tracks prompt tokens, completion tokens, latency, and estimated cost of LLM queries
and persists them to the token_usage table.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from git_reverse.storage.database import Database


# ── Model pricing profiles ───────────────────────────────────────────────────
# Price per 1M tokens (USD)
@dataclass(frozen=True)
class PriceProfile:
    prompt_rate_usd: float
    completion_rate_usd: float


_PRICING_TABLE: dict[str, PriceProfile] = {
    "openai/gpt-4o-mini": PriceProfile(0.150, 0.600),
    "openai/gpt-4o": PriceProfile(2.500, 10.000),
    "anthropic/claude-3-5-sonnet": PriceProfile(3.000, 15.000),
    "google/gemini-2.5-flash": PriceProfile(0.075, 0.300),
    "google/gemini-2.5-pro": PriceProfile(1.250, 5.000),
}

_DEFAULT_PRICE = PriceProfile(0.200, 0.800)  # Safe average fallback


# ── Usage Record ──────────────────────────────────────────────────────────────
@dataclass
class UsageRecord:
    id: str
    session_id: str
    prompt_tokens: int
    completion_tokens: int
    model: str
    cost_usd: float
    latency_ms: int
    created_at: str


class UsageTracker:
    """Logs and computes statistics of LLM usage."""

    def __init__(self, db: Database) -> None:
        self._db = db

    async def log_request(
        self,
        session_id: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        latency_ms: int,
    ) -> UsageRecord:
        """
        Record LLM metrics to SQLite and estimate cost.
        """
        # Resolve pricing
        profile = _PRICING_TABLE.get(model, _DEFAULT_PRICE)
        cost_usd = (
            (prompt_tokens * profile.prompt_rate_usd)
            + (completion_tokens * profile.completion_rate_usd)
        ) / 1_000_000.0

        record = UsageRecord(
            id=str(uuid.uuid4()),
            session_id=session_id,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            model=model,
            cost_usd=cost_usd,
            latency_ms=latency_ms,
            created_at=datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        )

        await self._db.conn.execute(
            """
            INSERT INTO token_usage (id, session_id, prompt_tokens, completion_tokens, model, cost_usd, latency_ms, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.id,
                record.session_id,
                record.prompt_tokens,
                record.completion_tokens,
                record.model,
                record.cost_usd,
                record.latency_ms,
                record.created_at,
            ),
        )
        await self._db.conn.commit()
        return record

    async def get_session_stats(self, session_id: str) -> dict[str, Any]:
        """
        Get aggregated usage statistics for a session.
        """
        async with self._db.conn.execute(
            """
            SELECT COUNT(*) as requests,
                   SUM(prompt_tokens) as total_prompt,
                   SUM(completion_tokens) as total_completion,
                   SUM(cost_usd) as total_cost,
                   AVG(latency_ms) as avg_latency
            FROM token_usage
            WHERE session_id = ?
            """,
            (session_id,),
        ) as cursor:
            row = await cursor.fetchone()

        if not row or row["requests"] == 0:
            return {
                "requests": 0,
                "total_prompt_tokens": 0,
                "total_completion_tokens": 0,
                "total_cost_usd": 0.0,
                "avg_latency_ms": 0.0,
            }

        return {
            "requests": row["requests"],
            "total_prompt_tokens": row["total_prompt"] or 0,
            "total_completion_tokens": row["total_completion"] or 0,
            "total_cost_usd": row["total_cost"] or 0.0,
            "avg_latency_ms": row["avg_latency"] or 0.0,
        }
