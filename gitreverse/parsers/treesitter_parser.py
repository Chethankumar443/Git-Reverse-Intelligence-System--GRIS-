import os
import sys
from pathlib import Path
import tree_sitter
from tree_sitter import Language, Parser as TSParser
from gitreverse.utils.logging import get_logger

logger = get_logger("parsers.treesitter")

SUPPORTED_LANGUAGES = {
    "python": "vendor/tree-sitter-python",
    "javascript": "vendor/tree-sitter-javascript",
    "typescript": "vendor/tree-sitter-typescript",
}

class TreeSitterParserBuilder:
    def __init__(self, build_dir: Path | None = None, vendor_dir: Path | None = None):
        self.workspace_dir = Path.cwd()
        self.build_dir = build_dir or self.workspace_dir / "build"
        self.vendor_dir = vendor_dir or self.workspace_dir / "vendor"
        
        self.build_dir.mkdir(parents=True, exist_ok=True)
        
        ext = ".dll" if sys.platform == "win32" else ".so"
        self.lib_path = self.build_dir / f"languages{ext}"
        
        self.languages = {}
        self._compiled = False

    def compile_languages(self) -> None:
        """Compile tree-sitter grammars from vendor folder."""
        if self._compiled:
            return
            
        grammar_paths = []
        languages_to_build = []
        
        for lang, rel_path in SUPPORTED_LANGUAGES.items():
            path = self.workspace_dir / rel_path
            
            # Special case for TS which has typescript/ subdir sometimes
            if lang == "typescript" and (path / "typescript").exists():
                path = path / "typescript"
                
            if path.exists():
                grammar_paths.append(str(path))
                languages_to_build.append(lang)
            else:
                logger.warning(f"Tree-sitter grammar source for {lang} not found at {path}")
                
        if not grammar_paths:
            logger.info("No grammar paths found to compile. Attempting to use existing library.")
            if self.lib_path.exists():
                self._compiled = True
                self._load_compiled_languages(list(SUPPORTED_LANGUAGES.keys()))
            return

        logger.info(f"Building tree-sitter library at {self.lib_path} for: {languages_to_build}")
        try:
            Language.build_library(
                str(self.lib_path),
                grammar_paths
            )
            self._compiled = True
            self._load_compiled_languages(languages_to_build)
        except Exception as e:
            logger.error(f"Failed to build tree-sitter library: {e}")
            if self.lib_path.exists():
                logger.info("Fallback: using previously compiled library.")
                self._compiled = True
                self._load_compiled_languages(list(SUPPORTED_LANGUAGES.keys()))
            else:
                raise

    def _load_compiled_languages(self, langs: list[str]) -> None:
        for lang in langs:
            try:
                self.languages[lang] = Language(str(self.lib_path), lang)
                logger.info(f"Loaded language parser for {lang}")
            except Exception as e:
                logger.error(f"Failed to load compiled parser for {lang}: {e}")

    def get_parser(self, language: str) -> TSParser | None:
        """Get an initialized tree-sitter Parser for the specified language."""
        if not self._compiled:
            try:
                self.compile_languages()
            except Exception as e:
                logger.error(f"Failed compilation during parser retrieval: {e}")
                return None
            
        lang_obj = self.languages.get(language)
        if not lang_obj:
            logger.warning(f"Language parser {language} not compiled/loaded.")
            return None
            
        parser = TSParser()
        parser.set_language(lang_obj)
        return parser
