"""
Go tree-sitter parser.

Extracts:
  - Import declarations.
  - Struct definitions / Type declarations.
  - Function declarations.
  - Method declarations.
"""

from __future__ import annotations

import tree_sitter_go
from tree_sitter import Language, Node

from git_reverse.analysis.parsers.base import BaseParser, ParsedSymbol


class GoParser(BaseParser):
    """Parses Go source code."""

    def _language(self) -> Language:
        return Language(tree_sitter_go.language())

    def _language_name(self) -> str:
        return "go"

    def _extract_symbols(self, root: Node, source: bytes, file_path: str) -> list[ParsedSymbol]:
        symbols: list[ParsedSymbol] = []

        # 1. Imports
        for node in self._find_all(root, "import_declaration"):
            # Can be import "foo" or import ( "foo" \n "bar" )
            for spec in self._find_all(node, "import_spec"):
                path_node = spec.child_by_field_name("path")
                if path_node:
                    path_str = self._node_text(path_node, source).strip('"')
                    symbol = ParsedSymbol(
                        type="import",
                        name=f"import {path_str}",
                        language="go",
                        file_path=file_path,
                        start_line=node.start_point[0] + 1,
                        end_line=node.end_point[0] + 1,
                        content=self._node_text(spec, source),
                        imports=[path_str],
                    )
                    symbols.append(symbol)

        # 2. Type definitions (Structs / Interfaces)
        for node in self._find_all(root, "type_declaration"):
            for spec in self._find_all(node, "type_spec"):
                name_node = spec.child_by_field_name("name")
                if not name_node:
                    continue
                name = self._node_text(name_node, source)

                type_type = "class"
                type_node = spec.child_by_field_name("type")
                if type_node and type_node.type == "struct_type":
                    type_type = "struct"
                elif type_node and type_node.type == "interface_type":
                    type_type = "trait"

                symbol = ParsedSymbol(
                    type=type_type,
                    name=name,
                    language="go",
                    file_path=file_path,
                    start_line=node.start_point[0] + 1,
                    end_line=node.end_point[0] + 1,
                    content=self._node_text(spec, source),
                )
                symbols.append(symbol)

        # 3. Functions and Methods
        for node in self._find_all(root, "function_declaration", "method_declaration"):
            name_node = node.child_by_field_name("name")
            if not name_node:
                continue
            name = self._node_text(name_node, source)

            # Check for receiver (method vs function)
            receiver_str = ""
            if node.type == "method_declaration":
                rec_node = node.child_by_field_name("receiver")
                if rec_node:
                    receiver_str = self._node_text(rec_node, source)
                    name = f"({receiver_str}).{name}"

            # Calls inside function body
            calls: list[str] = []
            for call_expr in self._find_all(node, "call_expression"):
                fn_expr = call_expr.child_by_field_name("function")
                if fn_expr:
                    calls.append(self._node_text(fn_expr, source))

            symbol = ParsedSymbol(
                type="function",
                name=name,
                language="go",
                file_path=file_path,
                start_line=node.start_point[0] + 1,
                end_line=node.end_point[0] + 1,
                content=self._node_text(node, source),
                calls=calls,
            )
            symbols.append(symbol)

        return symbols
