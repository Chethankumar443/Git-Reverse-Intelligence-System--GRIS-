from typing import Protocol
from pathlib import Path
from dataclasses import dataclass

@dataclass
class AnalysisContext:
    repo_path: Path
    repo_id: int
    commit_hash: str
    
@dataclass
class AnalysisResult:
    success: bool
    metrics: dict
    errors: list[str]

class Analyzer(Protocol):
    def analyze(self, context: AnalysisContext) -> AnalysisResult:
        """Run analysis on repository."""
        ...
    
    def supports(self, context: AnalysisContext) -> bool:
        """Check if this analyzer can handle the given context."""
        ...
