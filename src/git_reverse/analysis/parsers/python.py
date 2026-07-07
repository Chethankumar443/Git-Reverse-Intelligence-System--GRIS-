"""
Python tree-sitter parser.

Extracts:
  - Import statements (`import`, `from ... import`).
  - Classes (names, decorators, base classes, start/end lines).
  - Functions & async functions (names, decorators, parameters, start/end lines).
  - Calls (calls inside functions/classes to build dependency edges).
"""

from __future__ import annotations

import tree_sitter_python
from tree_sitter import Language, Node

from git_reverse.analysis.parsers.base import BaseParser, ParsedSymbol


class PythonParser(BaseParser):
    """Parses Python source code using tree-sitter-python."""

    def _language(self) -> Language:
        return Language(tree_sitter_python.language())

    def _language_name(self) -> str:
        return "python"

    def _extract_symbols(self, root: Node, source: bytes, file_path: str) -> list[ParsedSymbol]:
        symbols: list[ParsedSymbol] = []

        # 1. Extract imports at root level
        for node in self._find_all(root, "import_statement", "import_from_statement"):
            text = self._node_text(node, source)
            symbol = ParsedSymbol(
                type="import",
                name=text.split("\n")[0][:100],  # Keep name readable
                language="python",
                file_path=file_path,
                start_line=node.start_point[0] + 1,
                end_line=node.end_point[0] + 1,
                content=text,
            )
            # Try to resolve what modules are imported
            if node.type == "import_statement":
                # import foo, bar
                for child in node.children:
                    if child.type == "dotted_name":
                        symbol.imports.append(self._node_text(child, source))
            elif node.type == "import_from_statement":
                # from foo import bar
                dotted = self._find_first(node, "dotted_name")
                if dotted:
                    symbol.imports.append(self._node_text(dotted, source))
            symbols.append(symbol)

        # 2. Extract classes
        for node in self._find_all(root, "class_definition"):
            name_node = self._find_first(node, "identifier")
            if not name_node:
                continue
            name = self._node_text(name_node, source)

            # Base classes
            bases: list[str] = []
            arg_list = self._find_first(node, "argument_list")
            if arg_list:
                for child in arg_list.children:
                    if child.type in ("identifier", "attribute"):
                        bases.append(self._node_text(child, source))

            # Decorators
            decorators: list[str] = []
            decor_list = self._find_first(node, "decorator")
            if decor_list:
                decorators.append(self._node_text(decor_list, source))

            symbol = ParsedSymbol(
                type="class",
                name=name,
                language="python",
                file_path=file_path,
                start_line=node.start_point[0] + 1,
                end_line=node.end_point[0] + 1,
                content=self._node_text(node, source),
                bases=bases,
                decorators=decorators,
            )
            symbols.append(symbol)

        # 3. Extract functions
        for node in self._find_all(root, "function_definition"):
            name_node = self._find_first(node, "identifier")
            if not name_node:
                continue
            name = self._node_text(name_node, source)

            # Decorators
            decorators = []
            # In tree-sitter-python, decorators can be preceding siblings
            # or grouped. We search siblings immediately preceding or children
            prev = node.prev_sibling
            while prev and prev.type == "decorator":
                decorators.append(self._node_text(prev, source))
                prev = prev.prev_sibling

            # Find call names inside this function
            calls: list[str] = []
            for call_node in self._find_all(node, "call"):
                func_node = call_node.child_by_field_name("function")
                if func_node:
                    calls.append(self._node_text(func_node, source))

            symbol = ParsedSymbol(
                type="function",
                name=name,
                language="python",
                file_path=file_path,
                start_line=node.start_point[0] + 1,
                end_line=node.end_point[0] + 1,
                content=self._node_text(node, source),
                decorators=decorators,
                calls=calls,
            )
            symbols.append(symbol)

        return symbols
