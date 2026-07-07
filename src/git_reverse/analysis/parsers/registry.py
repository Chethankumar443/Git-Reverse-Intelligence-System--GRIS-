"""
Parser registry.

Manages language-specific parser instances, handles lazy initialization
to avoid importing parser modules and loading tree-sitter binaries until
needed, and maps file extensions to the correct parser instance.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from git_reverse.analysis.parsers.base import BaseParser


class ParserRegistry:
    """Registry mapping file suffixes to lazy-loaded parser instances."""

    def __init__(self) -> None:
        # Lazy cached instances
        self._parsers: dict[str, BaseParser] = {}

    def get_parser(self, suffix: str) -> BaseParser | None:
        """
        Return the appropriate BaseParser instance for the given file extension,
        or None if the extension is not supported.
        """
        ext = suffix.lower()
        
        # Resolve TypeScript / JSX variants to JS/TS parser
        if ext in (".js", ".jsx", ".mjs", ".cjs"):
            if "javascript" not in self._parsers:
                from git_reverse.analysis.parsers.javascript import JavaScriptParser
                self._parsers["javascript"] = JavaScriptParser(is_typescript=False)
            return self._parsers["javascript"]
            
        if ext in (".ts", ".tsx"):
            if "typescript" not in self._parsers:
                from git_reverse.analysis.parsers.javascript import JavaScriptParser
                self._parsers["typescript"] = JavaScriptParser(is_typescript=True)
            return self._parsers["typescript"]

        # Python
        if ext in (".py", ".pyw", ".pyi"):
            if "python" not in self._parsers:
                from git_reverse.analysis.parsers.python import PythonParser
                self._parsers["python"] = PythonParser()
            return self._parsers["python"]

        # Rust
        if ext == ".rs":
            if "rust" not in self._parsers:
                from git_reverse.analysis.parsers.rust import RustParser
                self._parsers["rust"] = RustParser()
            return self._parsers["rust"]

        # Go
        if ext == ".go":
            if "go" not in self._parsers:
                from git_reverse.analysis.parsers.go import GoParser
                self._parsers["go"] = GoParser()
            return self._parsers["go"]

        return None
