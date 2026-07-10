from typing import Protocol, Any

class Storage(Protocol):
    def save_repository(self, repo_data: dict) -> int:
        """Persist repository analysis results. Returns repo ID."""
        ...
    
    def load_repository(self, repo_id: int) -> dict:
        """Load repository analysis results."""
        ...
    
    def query(self, query: str, params: dict) -> list[dict[str, Any]]:
        """Execute a query against the knowledge graph."""
        ...
    
    def save_edge(self, source_id: int, source_type: str, target_id: int, target_type: str, relationship: str) -> None:
        """Save a relationship between entities."""
        ...
