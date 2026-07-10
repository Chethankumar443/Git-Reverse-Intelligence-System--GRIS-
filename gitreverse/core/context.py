from asyncio import Task
from dataclasses import dataclass, field
from pathlib import Path

@dataclass
class AnalysisContext:
    """Runtime context for an active analysis session."""
    url: str
    repo_id: int | None = None
    local_path: Path | None = None
    commit_hash: str | None = None
    task: Task | None = None
    is_complete: bool = False
    last_error: str | None = None
