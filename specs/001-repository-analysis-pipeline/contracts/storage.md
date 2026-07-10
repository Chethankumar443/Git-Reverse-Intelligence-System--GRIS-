# Storage Interface Contract

**Role**: Abstraction layer over SQLite + SQLModel. Ensures the rest of the pipeline doesn't couple directly to database implementation details. Manages the knowledge graph.

```python
from typing import Protocol, Any, List, Optional

class Storage(Protocol):
    """Interface for persistence and graph traversal."""
    
    # --- Repository Management ---
    def save_repository(self, url: str, local_path: str, commit_hash: str, size_bytes: int) -> int:
        """Upsert repo and return ID."""
        ...
        
    def get_repository(self, repo_id: int) -> Optional[dict]:
        ...

    # --- Pipeline Writes (Batch operations for performance) ---
    def bulk_save_files(self, repo_id: int, files: List[dict]) -> None:
        """Save parsed file metadata in batch."""
        ...

    def bulk_save_symbols(self, symbols: List[dict]) -> None:
        """Save extracted symbols in batch."""
        ...
        
    def save_framework_evidence(self, repo_id: int, name: str, evidence: dict) -> None:
        """Store framework detection with evidence."""
        ...

    # --- Knowledge Graph Writes ---
    def add_edges(self, edges: List[dict]) -> None:
        """
        Insert edges into the polymorphic knowledge_graph table.
        Expects: source_id, source_type, target_id, target_type, relationship, metadata.
        """
        ...

    # --- Traversals (Reads) ---
    def get_downstream_dependencies(self, symbol_id: int, max_depth: int = 10) -> List[dict]:
        """Recursive CTE traversal to find all callers/dependencies."""
        ...
        
    def raw_query(self, sql: str, params: tuple) -> List[dict]:
        """Escape hatch for complex analytics."""
        ...
```
