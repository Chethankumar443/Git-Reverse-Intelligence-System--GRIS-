from typing import Protocol, List
from pathlib import Path
from pydantic import BaseModel

class SymbolDef(BaseModel):
    name: str
    kind: str  # function, class, method, variable, import, export
    line_start: int
    line_end: int
    outbound_edges: List[dict] = []

class ParseResult(BaseModel):
    success: bool
    language: str
    ast_hash: str
    symbols: List[SymbolDef] = []
    imports: List[str] = []
    errors: List[str] = []

class Parser(Protocol):
    @property
    def language(self) -> str:
        ...
        
    def supports_file(self, file_path: Path) -> bool:
        ...

    def parse(self, file_path: Path, content: bytes) -> ParseResult:
        ...
