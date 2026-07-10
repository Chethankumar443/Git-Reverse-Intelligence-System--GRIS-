# Research Output: Repository Analysis Pipeline

**Date**: 2026-07-10
**Status**: Complete
**Deployment Model**: Single-machine, local-first

## Decision 1: AST Parsing Library
**Choice**: tree-sitter official Python bindings (not wrappers like tree-sitter-languages)

**Rationale**:
- Official bindings are highly stable in production
- Low overhead: direct C bindings, no Python wrapper layer
- Selective loading: load only the grammars you need (e.g., python, javascript, rust)
- Memory efficient: each grammar is ~1-2MB, loaded on demand

**Tradeoff**: Requires manual grammar installation per language, but this is acceptable for a plugin architecture where users install only the languages they analyze.

**Implementation**:
```python
import tree_sitter
from tree_sitter import Language, Parser

# Load language grammars dynamically
Language.build_library(
    'build/languages.so',
    ['vendor/tree-sitter-python', 'vendor/tree-sitter-javascript']
)

PYTHON_LANGUAGE = Language('build/languages.so', 'python')
parser = Parser()
parser.set_language(PYTHON_LANGUAGE)
```

---

## Decision 2: Database & Concurrency
**Choice**: SQLite in WAL mode + SQLModel

**Rationale**:
- WAL (Write-Ahead Logging) mode allows concurrent reads while writing
- SQLModel provides connection pooling and ORM layer
- Single-machine deployment means no need for distributed databases
- SQLite handles up to ~100k concurrent reads comfortably
- File-based storage aligns with local-first principle

**Configuration**:
```python
from sqlmodel import SQLModel, create_engine

engine = create_engine(
    "sqlite:///~/.gitreverse/cache.db",
    connect_args={"check_same_thread": False},
    pool_size=10,  # Connection pool for concurrent analysis tasks
    pool_pre_ping=True
)

# Enable WAL mode
with engine.connect() as conn:
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")  # Balance between safety and speed
    conn.execute("PRAGMA cache_size=10000")  # 10MB cache
```

**Tradeoff**: SQLite has a single-writer limit, but WAL mode allows readers to proceed during writes. For single-machine deployment with <10 concurrent analysis tasks, this is sufficient.

---

## Decision 3: Git Operations Library
**Choice**: pygit2 (libgit2 bindings)

**Rationale**:
- Native C-speed cloning and querying
- Lower memory consumption than pure-Python GitPython
- Supports advanced git operations (blame, diff, log) efficiently
- Required for incremental analysis (fast commit hash comparison)

**Tradeoff**: Requires libgit2 to be installed on the system. For packaging, we'll bundle libgit2 as a dependency or use PyInstaller with bundled binaries.

**Installation**:
```bash
# macOS
brew install libgit2

# Ubuntu/Debian
sudo apt-get install libgit2-dev

# Windows
# Use pre-built binaries or vcpkg
```

**Implementation**:
```python
import pygit2

# Clone repository
repo = pygit2.clone_repository(
    'https://github.com/user/repo',
    '/path/to/clone',
    callbacks=pygit2.RemoteCallbacks(credentials=pygit2.UserPass('token', 'x-oauth-basic'))
)

# Get commit hash for incremental analysis
head_commit = repo.head.target
```

---

## Decision 4: Incremental Analysis Strategy
**Choice**: Git commit hashes for change detection

**Rationale**:
- Comparing cached commit hashes is O(1) vs O(n) for file mtime comparison
- Immune to system clock skews and false positives
- Accurate: detects actual code changes, not just file touches
- Fast: single hash comparison vs walking entire file tree

**Implementation**:
```python
def should_reanalyze(repo_path: Path, cached_hash: str) -> bool:
    """Check if repository has changed since last analysis."""
    repo = pygit2.Repository(str(repo_path))
    current_hash = str(repo.head.target)
    return current_hash != cached_hash

def get_changed_files(repo_path: Path, old_hash: str, new_hash: str) -> list[Path]:
    """Get list of files changed between two commits."""
    repo = pygit2.Repository(str(repo_path))
    old_commit = repo.get(old_hash)
    new_commit = repo.get(new_hash)
    
    diff = repo.diff(old_commit, new_commit)
    changed_files = []
    for patch in diff:
        changed_files.append(Path(patch.delta.new_file.path))
    
    return changed_files
```

---

## Decision 5: Knowledge Graph Storage
**Choice**: Adjacency list in SQLite with recursive CTEs

**Rationale**:
- No need for dedicated graph database (Neo4j, ArangoDB) for single-machine deployment
- SQLite handles rapid traversals via recursive CTEs
- Adjacency list is simple, flexible, and well-supported
- Easy to export/import, query with standard SQL

**Schema**:
```sql
-- Nodes (symbols, files, modules, etc.)
CREATE TABLE nodes (
    id INTEGER PRIMARY KEY,
    type TEXT NOT NULL,  -- 'symbol', 'file', 'module', 'dependency'
    name TEXT NOT NULL,
    metadata JSON,
    repository_id INTEGER
);

-- Edges (relationships between nodes)
CREATE TABLE edges (
    id INTEGER PRIMARY KEY,
    source_id INTEGER REFERENCES nodes(id),
    target_id INTEGER REFERENCES nodes(id),
    relationship TEXT NOT NULL,  -- 'imports', 'calls', 'depends_on', 'contains'
    metadata JSON
);

-- Recursive CTE example: Find all dependencies of a symbol
WITH RECURSIVE dependencies AS (
    SELECT target_id, 1 AS depth
    FROM edges
    WHERE source_id = ? AND relationship = 'depends_on'
    
    UNION ALL
    
    SELECT e.target_id, d.depth + 1
    FROM edges e
    JOIN dependencies d ON e.source_id = d.target_id
    WHERE e.relationship = 'depends_on' AND d.depth < 10  -- Limit depth
)
SELECT n.* FROM nodes n
JOIN dependencies d ON n.id = d.target_id;
```

**Performance**: Recursive CTEs in SQLite can traverse 10k edges in <10ms. For repositories with <100k symbols, this is more than sufficient.

---

## Deployment Model: Single-Machine

### Constraints
- **Single user**: No multi-tenancy, no team collaboration in V1
- **Local storage**: All data in `~/.gitreverse/` (SQLite, cache, config)
- **Local compute**: All analysis runs on user's machine
- **No distributed systems**: No Redis, no message queues, no load balancers

### Concurrency Model
- **Concurrent analysis tasks**: Up to 5 simultaneous repository analyses (configurable)
- **Connection pool**: SQLModel pool_size=10 for database connections
- **Background jobs**: asyncio task queue for notifications, incremental analysis
- **Cancellation**: Immediate cancellation via asyncio.Task.cancel()

### Resource Limits
- **Memory**: <500MB for typical analysis (<100k LOC repository)
- **Disk**: <1GB per analyzed repository (including cache)
- **CPU**: Use all available cores for parallel file parsing
- **Network**: Rate-limited GitHub API calls (60/hour unauthenticated, 5000/hour with PAT)
