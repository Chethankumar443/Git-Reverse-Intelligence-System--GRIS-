"""
Rust tree-sitter parser.

Extracts:
  - Struct definitions.
  - Enum definitions.
  - Implementations (impl blocks).
  - Function definitions (`fn`).
  - Use declarations (imports).
"""

from __future__ import annotations

import tree_sitter_rust
from tree_sitter import Language, Node

from git_reverse.analysis.parsers.base import BaseParser, ParsedSymbol


class RustParser(BaseParser):
    """Parses Rust source code."""

    def _language(self) -> Language:
        return Language(tree_sitter_rust.language())

    def _language_name(self) -> str:
        return "rust"

    def _extract_symbols(self, root: Node, source: bytes, file_path: str) -> list[ParsedSymbol]:
        symbols: list[ParsedSymbol] = []

        # 1. Use statements (imports)
        for node in self._find_all(root, "use_declaration"):
            text = self._node_text(node, source)
            # Find the path component
            path_node = self._find_first(node, "scoped_identifier", "identifier")
            imports = [self._node_text(path_node, source)] if path_node else []
            symbol = ParsedSymbol(
                type="import",
                name=text.split("\n")[0][:100],
                language="rust",
                file_path=file_path,
                start_line=node.start_point[0] + 1,
                end_line=node.end_point[0] + 1,
                content=text,
                imports=imports,
            )
            symbols.append(symbol)

        # 2. Structs
        for node in self._find_all(root, "struct_item"):
            name_node = node.child_by_field_name("name")
            if not name_node:
                continue
            name = self._node_text(name_node, source)
            symbol = ParsedSymbol(
                type="struct",
                name=name,
                language="rust",
                file_path=file_path,
                start_line=node.start_point[0] + 1,
                end_line=node.end_point[0] + 1,
                content=self._node_text(node, source),
            )
            symbols.append(symbol)

        # 3. Enums
        for node in self._find_all(root, "enum_item"):
            name_node = node.child_by_field_name("name")
            if not name_node:
                continue
            name = self._node_text(name_node, source)
            symbol = ParsedSymbol(
                type="class",  # Treat Enum as a class equivalent for high-level graphs
                name=name,
                language="rust",
                file_path=file_path,
                start_line=node.start_point[0] + 1,
                end_line=node.end_point[0] + 1,
                content=self._node_text(node, source),
            )
            symbols.append(symbol)

        # 4. Impl blocks
        for node in self._find_all(root, "impl_item"):
            type_node = node.child_by_field_name("type")
            trait_node = node.child_by_field_name("trait")

            target_name = self._node_text(type_node, source) if type_node else "Unknown"
            if trait_node:
                trait_name = self._node_text(trait_node, source)
                name = f"impl {trait_name} for {target_name}"
            else:
                name = f"impl {target_name}"

            symbol = ParsedSymbol(
                type="class",  # Represents class-level implementation logic in graph
                name=name,
                language="rust",
                file_path=file_path,
                start_line=node.start_point[0] + 1,
                end_line=node.end_point[0] + 1,
                content=self._node_text(node, source),
                bases=[self._node_text(trait_node, source)] if trait_node else [],
            )
            symbols.append(symbol)

        # 5. Functions & Methods
        for node in self._find_all(root, "function_item"):
            name_node = node.child_by_field_name("name")
            if not name_node:
                continue
            name = self._node_text(name_node, source)

            # Calls inside function
            calls: list[str] = []
            for call_expr in self._find_all(node, "call_expression"):
                fn_expr = call_expr.child_by_field_name("function")
                if fn_expr:
                    calls.append(self._node_text(fn_expr, source))

            symbol = ParsedSymbol(
                type="function",
                name=name,
                language="rust",
                file_path=file_path,
                start_line=node.start_point[0] + 1,
                end_line=node.end_point[0] + 1,
                content=self._node_text(node, source),
                calls=calls,
            )
            symbols.append(symbol)

        return symbols
