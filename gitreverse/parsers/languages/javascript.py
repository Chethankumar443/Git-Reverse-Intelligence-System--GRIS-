import hashlib
from pathlib import Path
from tree_sitter import Parser as TSParser
from gitreverse.parsers.base import ParseResult, SymbolDef
from gitreverse.utils.logging import get_logger

logger = get_logger("parsers.javascript")

# tree-sitter node types for JS/TS symbols
JS_SYMBOL_KINDS = {
    "function_declaration": "function",
    "generator_function_declaration": "function",
    "arrow_function": "function",
    "class_declaration": "class",
    "method_definition": "method",
    "lexical_declaration": "variable",
    "variable_declaration": "variable",
}

IMPORT_NODE_TYPES = {
    "import_statement",
    "import_declaration",
}

class JavaScriptParser:
    def __init__(self, typescript: bool = False):
        self._typescript = typescript

    @property
    def language(self) -> str:
        return "typescript" if self._typescript else "javascript"

    def supports_file(self, file_path: Path) -> bool:
        if self._typescript:
            return file_path.suffix in (".ts", ".tsx")
        return file_path.suffix in (".js", ".mjs", ".cjs", ".jsx")

    def parse(self, file_path: Path, content: bytes, ts_parser: TSParser | None = None) -> ParseResult:
        ast_hash = hashlib.sha256(content).hexdigest()
        symbols: list[SymbolDef] = []
        imports: list[str] = []
        errors: list[str] = []

        if ts_parser is None:
            return ParseResult(
                success=False,
                language=self.language,
                ast_hash=ast_hash,
                errors=["No parser provided - tree-sitter grammar not loaded"]
            )

        try:
            tree = ts_parser.parse(content)
            root = tree.root_node

            for node in self._traverse(root):
                # Named function / class declarations
                if node.type in JS_SYMBOL_KINDS:
                    name_node = node.child_by_field_name("name")
                    name = name_node.text.decode("utf-8", errors="replace") if name_node else "<anonymous>"
                    symbols.append(SymbolDef(
                        name=name,
                        kind=JS_SYMBOL_KINDS[node.type],
                        line_start=node.start_point[0] + 1,
                        line_end=node.end_point[0] + 1,
                    ))

                # Imports
                elif node.type in IMPORT_NODE_TYPES:
                    imports.append(node.text.decode("utf-8", errors="replace").strip())

        except Exception as e:
            logger.error(f"Failed to parse JS/TS file {file_path}: {e}")
            errors.append(str(e))
            return ParseResult(success=False, language=self.language, ast_hash=ast_hash, errors=errors)

        return ParseResult(
            success=True,
            language=self.language,
            ast_hash=ast_hash,
            symbols=symbols,
            imports=imports,
            errors=errors,
        )

    def _traverse(self, node):
        yield node
        for child in node.children:
            yield from self._traverse(child)
