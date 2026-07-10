from typing import Protocol
from pathlib import Path
from dataclasses import dataclass

@dataclass
class SymbolDef:
    name: str
    kind: str
    line_start: int
    line_end: int

@dataclass
class ParseResult:
    success: bool
    symbols: list[SymbolDef]
    imports: list[str]
    errors: list[str]

class Parser(Protocol):
    def parse(self, file_path: Path) -> ParseResult:
        """Parse a single file and extract symbols."""
        ...
    
    def supports_language(self, language: str) -> bool:
        """Check if this parser supports the given language."""
        ...
