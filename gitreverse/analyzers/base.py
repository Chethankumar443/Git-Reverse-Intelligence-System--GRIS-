from pathlib import Path
from typing import List
from pydantic import BaseModel

class AnalysisContext(BaseModel):
    repo_id: int
    local_path: Path
    commit_hash: str
    files: List[dict] = []

    class Config:
        arbitrary_types_allowed = True

class AnalysisResult(BaseModel):
    analyzer_name: str
    success: bool
    metrics: dict = {}
    errors: List[str] = []
    extracted_entities: List[dict] = []

class Analyzer:
    """Base interface all analyzers must implement."""
    @property
    def name(self) -> str:
        raise NotImplementedError

    def supports(self, context: AnalysisContext) -> bool:
        raise NotImplementedError

    def analyze(self, context: AnalysisContext) -> AnalysisResult:
        raise NotImplementedError
