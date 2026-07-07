"""
JavaScript/TypeScript tree-sitter parser.

Extracts:
  - Class definitions and constructor/methods.
  - Function declarations, arrow functions, and method definitions.
  - ES6 imports and CommonJS requires.
  - Function/method calls inside bodies.
"""

from __future__ import annotations

import tree_sitter_javascript
import tree_sitter_typescript
from tree_sitter import Language, Node

from git_reverse.analysis.parsers.base import BaseParser, ParsedSymbol


class JavaScriptParser(BaseParser):
    """Parses JavaScript/TypeScript source code."""

    def __init__(self, is_typescript: bool = False) -> None:
        self._is_ts = is_typescript
        super().__init__()

    def _language(self) -> Language:
        if self._is_ts:
            return Language(tree_sitter_typescript.language_typescript())
        return Language(tree_sitter_javascript.language())

    def _language_name(self) -> str:
        return "typescript" if self._is_ts else "javascript"

    def _extract_symbols(self, root: Node, source: bytes, file_path: str) -> list[ParsedSymbol]:
        symbols: list[ParsedSymbol] = []
        lang = self._language_name()

        # 1. Imports (ES6 imports & requires)
        for node in self._find_all(root, "import_statement", "lexical_declaration", "variable_declaration"):
            text = self._node_text(node, source)

            # Direct ES6 Import: import foo from 'bar'
            if node.type == "import_statement":
                source_node = node.child_by_field_name("source")
                source_text = self._node_text(source_node, source) if source_node else ""
                source_clean = source_text.strip("'\"")

                symbol = ParsedSymbol(
                    type="import",
                    name=text.split("\n")[0][:100],
                    language=lang,
                    file_path=file_path,
                    start_line=node.start_point[0] + 1,
                    end_line=node.end_point[0] + 1,
                    content=text,
                    imports=[source_clean] if source_clean else [],
                )
                symbols.append(symbol)
            else:
                # Require pattern: const foo = require('bar')
                if "require(" in text:
                    calls = self._find_all(node, "call_expression")
                    for c in calls:
                        func_node = c.child_by_field_name("function")
                        if func_node and self._node_text(func_node, source) == "require":
                            args = c.child_by_field_name("arguments")
                            if args and len(args.children) > 1:
                                req_target = self._node_text(args.children[1], source).strip("'\"")
                                symbol = ParsedSymbol(
                                    type="import",
                                    name=f"require({req_target})",
                                    language=lang,
                                    file_path=file_path,
                                    start_line=node.start_point[0] + 1,
                                    end_line=node.end_point[0] + 1,
                                    content=text,
                                    imports=[req_target],
                                )
                                symbols.append(symbol)

        # 2. Classes
        for node in self._find_all(root, "class_declaration", "class"):
            name_node = node.child_by_field_name("name")
            if not name_node:
                continue
            name = self._node_text(name_node, source)

            # Heritage / Extends
            bases: list[str] = []
            heritage = self._find_first(node, "class_heritage")
            if heritage:
                # extends parent
                parent_identifier = self._find_first(heritage, "identifier")
                if parent_identifier:
                    bases.append(self._node_text(parent_identifier, source))

            symbol = ParsedSymbol(
                type="class",
                name=name,
                language=lang,
                file_path=file_path,
                start_line=node.start_point[0] + 1,
                end_line=node.end_point[0] + 1,
                content=self._node_text(node, source),
                bases=bases,
            )
            symbols.append(symbol)

        # 3. Functions
        fn_types = ("function_declaration", "generator_function_declaration", "method_definition")
        for node in self._find_all(root, *fn_types):
            name_node = node.child_by_field_name("name")
            if not name_node:
                continue
            name = self._node_text(name_node, source)

            calls = []
            for call_expr in self._find_all(node, "call_expression"):
                fn_expr = call_expr.child_by_field_name("function")
                if fn_expr:
                    calls.append(self._node_text(fn_expr, source))

            symbol = ParsedSymbol(
                type="function",
                name=name,
                language=lang,
                file_path=file_path,
                start_line=node.start_point[0] + 1,
                end_line=node.end_point[0] + 1,
                content=self._node_text(node, source),
                calls=calls,
            )
            symbols.append(symbol)

        # Arrow Functions assigned to variables: const foo = () => {}
        for node in self._find_all(root, "lexical_declaration", "variable_declaration"):
            arrow = self._find_first(node, "arrow_function")
            if arrow:
                declarator = self._find_first(node, "variable_declarator")
                if declarator:
                    name_id = declarator.child_by_field_name("name")
                    if name_id:
                        name = self._node_text(name_id, source)
                        calls = []
                        for call_expr in self._find_all(arrow, "call_expression"):
                            fn_expr = call_expr.child_by_field_name("function")
                            if fn_expr:
                                calls.append(self._node_text(fn_expr, source))

                        symbol = ParsedSymbol(
                            type="function",
                            name=name,
                            language=lang,
                            file_path=file_path,
                            start_line=node.start_point[0] + 1,
                            end_line=node.end_point[0] + 1,
                            content=self._node_text(node, source),
                            calls=calls,
                        )
                        symbols.append(symbol)

        return symbols
