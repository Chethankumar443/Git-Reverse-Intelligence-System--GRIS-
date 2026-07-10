# Parser Interface Contract

**Role**: Parsers convert raw source files into structured AST representations and extract symbols. They are language-specific plugins (wrapping tree-sitter grammars).

```python
from typing import Protocol, List
from pathlib import Path
from pydantic import BaseModel

class SymbolDef(BaseModel):
    """Extracted symbol definition (evidence-backed)."""
    name: str
    kind: str  # function, class, variable, import, export
    line_start: int
    line_end: int
    # Relationship evidence (e.g., this function calls X)
    outbound_edges: List[dict] = []

class ParseResult(BaseModel):
    success: bool
    language: str
    ast_hash: str
    symbols: List[SymbolDef]
    errors: List[str]

class Parser(Protocol):
    """Plugin interface for language-specific AST parsers."""
    
    @property
    def language(self) -> str:
        """Language identifier (e.g., 'python', 'rust')."""
        ...
        
    def supports_file(self, file_path: Path) -> bool:
        """Check if parser handles this file extension/content."""
        ...

    def parse(self, file_path: Path, content: bytes) -> ParseResult:
        """
        Parse file content into AST and extract symbols.
        Operates purely in memory. Deterministic.
        """
        ...
```
