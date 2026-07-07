-- Migration 002: Token usage tracking for LLM reasoning layer

CREATE TABLE IF NOT EXISTS token_usage (
    id                 TEXT PRIMARY KEY,
    session_id         TEXT REFERENCES sessions(id) ON DELETE CASCADE,
    prompt_tokens      INTEGER,
    completion_tokens  INTEGER,
    model              TEXT,
    cost_usd           REAL,
    latency_ms         INTEGER,
    created_at         TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);
