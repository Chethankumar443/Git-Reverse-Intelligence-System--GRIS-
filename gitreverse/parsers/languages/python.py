import hashlib
from pathlib import Path
from tree_sitter import Parser as TSParser
from gitreverse.parsers.base import ParseResult, SymbolDef
from gitreverse.utils.logging import get_logger

logger = get_logger("parsers.python")

# tree-sitter node types for Python symbols
PYTHON_SYMBOL_KINDS = {
    "function_definition": "function",
    "async_function_definition": "function",
    "class_definition": "class",
}

class PythonParser:
    @property
    def language(self) -> str:
        return "python"

    def supports_file(self, file_path: Path) -> bool:
        return file_path.suffix in (".py",)

    def parse(self, file_path: Path, content: bytes, ts_parser: TSParser | None = None) -> ParseResult:
        ast_hash = hashlib.sha256(content).hexdigest()
        symbols: list[SymbolDef] = []
        imports: list[str] = []
        errors: list[str] = []

        if ts_parser is None:
            return ParseResult(
                success=False,
                language="python",
                ast_hash=ast_hash,
                errors=["No parser provided - tree-sitter grammar not loaded"]
            )

        try:
            tree = ts_parser.parse(content)
            root = tree.root_node

            for node in self._traverse(root):
                # Extract symbols (functions and classes)
                if node.type in PYTHON_SYMBOL_KINDS:
                    name_node = node.child_by_field_name("name")
                    if name_node:
                        symbols.append(SymbolDef(
                            name=name_node.text.decode("utf-8", errors="replace"),
                            kind=PYTHON_SYMBOL_KINDS[node.type],
                            line_start=node.start_point[0] + 1,
                            line_end=node.end_point[0] + 1,
                        ))

                # Extract imports
                elif node.type == "import_statement":
                    imports.append(node.text.decode("utf-8", errors="replace").strip())
                elif node.type == "import_from_statement":
                    imports.append(node.text.decode("utf-8", errors="replace").strip())

        except Exception as e:
            logger.error(f"Failed to parse Python file {file_path}: {e}")
            errors.append(str(e))
            return ParseResult(success=False, language="python", ast_hash=ast_hash, errors=errors)

        return ParseResult(
            success=True,
            language="python",
            ast_hash=ast_hash,
            symbols=symbols,
            imports=imports,
            errors=errors,
        )

    def _traverse(self, node):
        yield node
        for child in node.children:
            yield from self._traverse(child)
