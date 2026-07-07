-- ─────────────────────────────────────────────────────────────────────────────
-- Git Reverse — Initial SQLite Schema
-- Migration: 001_initial
-- ─────────────────────────────────────────────────────────────────────────────
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

-- ── Schema Version Tracking ───────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS schema_migrations (
    version     INTEGER PRIMARY KEY,
    applied_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

-- ── Repositories ──────────────────────────────────────────────────────────────
-- Represents a repository that has been ingested into the platform.
CREATE TABLE IF NOT EXISTS repositories (
    id                TEXT    PRIMARY KEY,       -- UUID v4
    url               TEXT    NOT NULL,           -- Original clone URL or local path
    name              TEXT    NOT NULL,           -- e.g. "fastapi"
    local_path        TEXT,                       -- Absolute path to the local cache
    primary_language  TEXT,
    size_bytes        INTEGER DEFAULT 0,
    cloned_at         TEXT,                       -- ISO 8601
    last_analyzed_at  TEXT,
    analysis_status   TEXT    NOT NULL DEFAULT 'pending',  -- pending|running|complete|failed
    error_message     TEXT,
    metadata          TEXT    DEFAULT '{}'        -- JSON blob for extension metadata
);

CREATE INDEX IF NOT EXISTS idx_repos_url ON repositories(url);
CREATE INDEX IF NOT EXISTS idx_repos_status ON repositories(analysis_status);

-- ── Knowledge Graph Nodes ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS nodes (
    id          TEXT    PRIMARY KEY,    -- UUID v4
    repo_id     TEXT    NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
    type        TEXT    NOT NULL,       -- Function | Class | File | Package | Endpoint | …
    name        TEXT    NOT NULL,
    file_path   TEXT,
    start_line  INTEGER,
    end_line    INTEGER,
    content     TEXT,                  -- Raw source (trimmed to 4096 chars)
    metadata    TEXT    DEFAULT '{}'   -- JSON: framework tags, complexity score, etc.
);

CREATE INDEX IF NOT EXISTS idx_nodes_repo   ON nodes(repo_id);
CREATE INDEX IF NOT EXISTS idx_nodes_type   ON nodes(repo_id, type);
CREATE INDEX IF NOT EXISTS idx_nodes_name   ON nodes(repo_id, name);

-- ── Knowledge Graph Edges ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS edges (
    source_id     TEXT NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
    target_id     TEXT NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
    relation_type TEXT NOT NULL,   -- CALLS | IMPORTS | INHERITS | DEPENDS_ON | HANDLES | …
    metadata      TEXT DEFAULT '{}',
    PRIMARY KEY (source_id, target_id, relation_type)
);

CREATE INDEX IF NOT EXISTS idx_edges_source ON edges(source_id);
CREATE INDEX IF NOT EXISTS idx_edges_target ON edges(target_id);

-- ── Sessions ──────────────────────────────────────────────────────────────────
-- A session represents a single interactive analysis conversation.
CREATE TABLE IF NOT EXISTS sessions (
    id            TEXT PRIMARY KEY,   -- Format: GR-YYYYMMDD-XXXX
    repo_id       TEXT REFERENCES repositories(id) ON DELETE SET NULL,
    mode          TEXT NOT NULL DEFAULT 'explore',
    model         TEXT NOT NULL,
    username      TEXT,
    summary       TEXT,              -- LLM-generated session summary
    created_at    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    updated_at    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    is_archived   INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_sessions_repo ON sessions(repo_id);
CREATE INDEX IF NOT EXISTS idx_sessions_created ON sessions(created_at DESC);

-- ── Messages ──────────────────────────────────────────────────────────────────
-- Each row is a single turn in the conversation (user or assistant).
CREATE TABLE IF NOT EXISTS messages (
    id          TEXT    PRIMARY KEY,
    session_id  TEXT    NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    role        TEXT    NOT NULL CHECK(role IN ('user', 'assistant', 'system')),
    content     TEXT    NOT NULL,
    model       TEXT,
    tokens_used INTEGER,
    created_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id, created_at);

-- ── Bookmarks ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS bookmarks (
    id          TEXT    PRIMARY KEY,
    session_id  TEXT    NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    message_id  TEXT    REFERENCES messages(id) ON DELETE CASCADE,
    label       TEXT    NOT NULL,
    note        TEXT,
    created_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

-- ── Settings Store ────────────────────────────────────────────────────────────
-- Key/value store for persistent user preferences (supplement to env vars).
CREATE TABLE IF NOT EXISTS settings (
    key         TEXT PRIMARY KEY,
    value       TEXT NOT NULL,
    updated_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

-- ── Mark migration as applied ─────────────────────────────────────────────────
INSERT OR IGNORE INTO schema_migrations (version) VALUES (1);
