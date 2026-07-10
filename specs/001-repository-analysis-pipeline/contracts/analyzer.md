# Analyzer Interface Contract

**Role**: Analyzers extract specific domain knowledge (frameworks, architecture, dependencies) from the repository files or ASTs. They implement a plugin architecture allowing new languages/frameworks to be added without modifying the core pipeline.

```python
from typing import Protocol, List, Optional
from pathlib import Path
from pydantic import BaseModel

class AnalysisContext(BaseModel):
    """Context passed to all analyzers."""
    repo_id: int
    local_path: Path
    commit_hash: str
    files: List[dict]  # Reference to parsed files metadata

class AnalysisResult(BaseModel):
    """Standardized output from any analyzer."""
    analyzer_name: str
    success: bool
    metrics: dict
    errors: List[str]
    # Data to be persisted (extracted framework, arch nodes, etc)
    extracted_entities: List[dict] 

class Analyzer(Protocol):
    """Plugin interface for all analysis modules."""
    
    @property
    def name(self) -> str:
        """Unique name of the analyzer (e.g., 'express-detector')."""
        ...
        
    def supports(self, context: AnalysisContext) -> bool:
        """
        Fast check if this analyzer should run. 
        e.g., A Python analyzer returns False if no .py files exist.
        """
        ...

    def analyze(self, context: AnalysisContext) -> AnalysisResult:
        """
        Execute the analysis. MUST NOT mutate the repository files.
        MUST return evidence-backed entities (file path, line numbers).
        """
        ...
```
