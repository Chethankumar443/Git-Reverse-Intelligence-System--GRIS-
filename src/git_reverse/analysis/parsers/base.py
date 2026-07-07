"""
Abstract base class for all language-specific tree-sitter parsers.

Contract:
  - `parse(file_path)` reads the file, builds the AST, and extracts symbols.
  - It never raises — errors are caught and returned as a failed ParseResult.
  - All subclasses must implement `_extract_symbols()`.

Each parser produces a list of `ParsedSymbol` objects representing the
structured knowledge that will be stored as graph nodes.
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from tree_sitter import Language, Node, Parser

from git_reverse.core.logging import get_logger

log = get_logger(__name__)


# ── Data Contracts ────────────────────────────────────────────────────────────
@dataclass
class ParsedSymbol:
    """
    A single symbol extracted from an AST — function, class, import, module.

    This is the unit of knowledge that becomes a graph Node in the SQLite DB.
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: str = ""           # "function" | "class" | "import" | "module" | "struct" | "trait"
    name: str = ""
    language: str = ""
    file_path: str = ""
    start_line: int = 0
    end_line: int = 0
    content: str = ""        # The raw source text of this symbol
    metadata: dict[str, Any] = field(default_factory=dict)

    # Relationship data — resolved into edges by KnowledgeGraphBuilder
    calls: list[str] = field(default_factory=list)     # names of called functions
    imports: list[str] = field(default_factory=list)   # imported module names
    bases: list[str] = field(default_factory=list)     # parent classes
    decorators: list[str] = field(default_factory=list)


@dataclass
class ParseResult:
    """The outcome of parsing a single file."""

    file_path: str
    language: str
    symbols: list[ParsedSymbol] = field(default_factory=list)
    error: str | None = None

    @property
    def success(self) -> bool:
        return self.error is None

    @property
    def node_count(self) -> int:
        return len(self.symbols)


# ── Base Parser ───────────────────────────────────────────────────────────────
class BaseParser(ABC):
    """
    Abstract tree-sitter parser.

    Subclasses implement `_language()` to return the tree-sitter Language
    object and `_extract_symbols()` to walk the AST and collect ParsedSymbols.
    """

    def __init__(self) -> None:
        lang = self._language()
        self._parser: Parser = Parser(lang)
        self._lang_name: str = self._language_name()

    @abstractmethod
    def _language(self) -> Language:
        """Return the tree-sitter Language for this parser."""

    @abstractmethod
    def _language_name(self) -> str:
        """Return the canonical language name string (e.g. 'python')."""

    @abstractmethod
    def _extract_symbols(self, root: Node, source: bytes, file_path: str) -> list[ParsedSymbol]:
        """Walk the AST root and return all extracted symbols."""

    # ── Public API ────────────────────────────────────────────────────────────
    def parse(self, file_path: Path) -> ParseResult:
        """
        Parse a single file and return a ParseResult.

        Reads the file as UTF-8 (replacing bad bytes), parses with tree-sitter,
        then delegates symbol extraction to the subclass.

        Never raises — errors are captured in ParseResult.error.
        """
        try:
            source = file_path.read_bytes()
        except OSError as exc:
            return ParseResult(
                file_path=str(file_path),
                language=self._lang_name,
                error=f"Cannot read file: {exc}",
            )

        try:
            tree = self._parser.parse(source)
        except Exception as exc:  # noqa: BLE001
            return ParseResult(
                file_path=str(file_path),
                language=self._lang_name,
                error=f"Tree-sitter parse error: {exc}",
            )

        if tree.root_node.has_error:
            # Parse succeeded but the tree contains syntax errors — still extract
            log.debug("ast_parse_has_errors", path=str(file_path), lang=self._lang_name)

        try:
            symbols = self._extract_symbols(tree.root_node, source, str(file_path))
        except Exception as exc:  # noqa: BLE001
            log.error(
                "symbol_extraction_failed",
                path=str(file_path),
                lang=self._lang_name,
                error=str(exc),
            )
            return ParseResult(
                file_path=str(file_path),
                language=self._lang_name,
                error=f"Symbol extraction failed: {exc}",
            )

        # Always prepend a "module" symbol for the file itself
        module_symbol = ParsedSymbol(
            type="module",
            name=file_path.stem,
            language=self._lang_name,
            file_path=str(file_path),
            start_line=1,
            end_line=_line_count(source),
        )
        return ParseResult(
            file_path=str(file_path),
            language=self._lang_name,
            symbols=[module_symbol, *symbols],
        )

    # ── Shared helpers ────────────────────────────────────────────────────────
    @staticmethod
    def _node_text(node: Node, source: bytes) -> str:
        """Return the UTF-8 decoded source text of an AST node."""
        return source[node.start_byte:node.end_byte].decode("utf-8", errors="replace")

    @staticmethod
    def _find_first(node: Node, *type_names: str) -> Node | None:
        """BFS: find the first child node matching any of the given types."""
        queue = list(node.children)
        while queue:
            child = queue.pop(0)
            if child.type in type_names:
                return child
            queue.extend(child.children)
        return None

    @staticmethod
    def _find_all(node: Node, *type_names: str) -> list[Node]:
        """DFS: collect all descendant nodes matching any of the given types."""
        results: list[Node] = []
        stack = list(node.children)
        while stack:
            child = stack.pop()
            if child.type in type_names:
                results.append(child)
            stack.extend(reversed(child.children))
        return results

    @staticmethod
    def _direct_children_of_type(node: Node, *type_names: str) -> list[Node]:
        """Return immediate children matching any of the given types."""
        return [c for c in node.children if c.type in type_names]


# ── Helpers ───────────────────────────────────────────────────────────────────
def _line_count(source: bytes) -> int:
    return source.count(b"\n") + 1
