import asyncio
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import AsyncIterator, List
from datetime import datetime

from gitreverse.git.clone import clone_repository
from gitreverse.git.diff import get_current_commit_hash, should_reanalyze, get_changed_files
from gitreverse.parsers.treesitter_parser import TreeSitterParserBuilder
from gitreverse.parsers.languages.python import PythonParser
from gitreverse.parsers.languages.javascript import JavaScriptParser
from gitreverse.analyzers.dependency_analyzer import DependencyAnalyzer
from gitreverse.analyzers.framework_detector import FrameworkDetector
from gitreverse.analyzers.base import AnalysisContext
from gitreverse.storage.database import DatabaseManager
from gitreverse.utils.config import load_config
from gitreverse.utils.logging import get_logger

logger = get_logger("core.pipeline")

EXTENSION_TO_LANGUAGE = {
    ".py": "python",
    ".js": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
}

SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build", ".mypy_cache"}


@dataclass
class PipelineProgress:
    stage: str
    message: str
    percent: float = 0.0


class AnalysisPipeline:
    def __init__(self, db: DatabaseManager | None = None):
        self.config = load_config()
        self.db = db or DatabaseManager()
        self._cache_dir = Path("~/.gitreverse/repos").expanduser()
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._parser_builder = TreeSitterParserBuilder()
        self._language_parsers = {
            "python": PythonParser(),
            "javascript": JavaScriptParser(typescript=False),
            "typescript": JavaScriptParser(typescript=True),
        }
        self._analyzers = [DependencyAnalyzer(), FrameworkDetector()]

    async def run(
        self,
        url: str,
        token: str | None = None,
        incremental: bool = False,
    ) -> AsyncIterator[PipelineProgress]:
        """
        Main analysis pipeline. Yields PipelineProgress updates throughout.
        Designed to run as an asyncio task so the TUI stays non-blocking.
        """
        repo_name = url.rstrip("/").split("/")[-1]
        local_path = self._cache_dir / repo_name

        # --- Stage 1: Clone ---
        yield PipelineProgress("clone", f"Cloning {url}...", 0.0)
        await asyncio.sleep(0)  # Yield control to event loop

        start = time.monotonic()
        loop = asyncio.get_event_loop()

        try:
            await loop.run_in_executor(
                None, lambda: clone_repository(url, local_path, token)
            )
        except Exception as e:
            yield PipelineProgress("error", f"Clone failed: {e}", 0.0)
            return

        clone_time = time.monotonic() - start
        commit_hash = get_current_commit_hash(local_path)

        # Check if already analyzed at this commit
        size_bytes = sum(
            f.stat().st_size
            for f in local_path.rglob("*")
            if f.is_file() and not any(d in f.parts for d in SKIP_DIRS)
        )

        repo_id = self.db.save_repository(
            url=url,
            local_path=str(local_path),
            commit_hash=commit_hash,
            size_bytes=size_bytes,
        )
        yield PipelineProgress("clone", f"Cloned in {clone_time:.1f}s — commit {commit_hash[:8]}", 20.0)
        await asyncio.sleep(0)

        # --- Stage 2: Discover files ---
        yield PipelineProgress("scan", "Scanning files...", 25.0)
        all_files = self._collect_files(local_path)
        yield PipelineProgress("scan", f"Found {len(all_files)} source files", 30.0)
        await asyncio.sleep(0)

        # --- Stage 3: AST Parsing ---
        yield PipelineProgress("parse", "Parsing AST...", 30.0)
        await asyncio.sleep(0)

        # Compile grammars (can be slow on first run)
        await loop.run_in_executor(None, self._parser_builder.compile_languages)

        file_records = []
        symbol_records = []
        total = max(len(all_files), 1)

        for idx, (abs_path, rel_path, lang) in enumerate(all_files):
            try:
                content = abs_path.read_bytes()
                ts_parser = self._parser_builder.get_parser(lang)
                lang_parser = self._language_parsers.get(lang)

                if lang_parser and ts_parser:
                    result = lang_parser.parse(abs_path, content, ts_parser)
                    ast_hash = result.ast_hash

                    file_records.append({
                        "path": str(rel_path),
                        "language": lang,
                        "size_bytes": len(content),
                        "last_modified": datetime.utcnow(),
                        "ast_hash": ast_hash,
                    })

                    for sym in result.symbols:
                        symbol_records.append({
                            "name": sym.name,
                            "kind": sym.kind,
                            "line_start": sym.line_start,
                            "line_end": sym.line_end,
                        })
                else:
                    file_records.append({
                        "path": str(rel_path),
                        "language": lang,
                        "size_bytes": len(content),
                        "last_modified": datetime.utcnow(),
                        "ast_hash": "",
                    })

            except Exception as e:
                logger.error(f"Parse error for {rel_path}: {e}")

            pct = 30.0 + (idx / total) * 35.0
            if idx % 20 == 0:
                yield PipelineProgress("parse", f"Parsed {idx+1}/{total} files", pct)
                await asyncio.sleep(0)

        self.db.bulk_save_files(repo_id, file_records)
        yield PipelineProgress("parse", f"Extracted {len(symbol_records)} symbols from {len(file_records)} files", 65.0)
        await asyncio.sleep(0)

        # --- Stage 4: Analyzers (dependency + framework) ---
        yield PipelineProgress("analyze", "Running analyzers...", 70.0)
        await asyncio.sleep(0)

        context = AnalysisContext(
            repo_id=repo_id,
            local_path=local_path,
            commit_hash=commit_hash,
        )

        for analyzer in self._analyzers:
            if not analyzer.supports(context):
                continue
            result = await loop.run_in_executor(None, lambda a=analyzer: a.analyze(context))

            if hasattr(result, "extracted_entities"):
                if analyzer.name == "dependency-analyzer":
                    self.db.bulk_save_files(repo_id, [])  # already done
                    # Save to dependency table
                    from gitreverse.models.dependency import Dependency
                    from sqlmodel import Session
                    with self.db.get_session() as session:
                        for dep in result.extracted_entities:
                            from gitreverse.models.dependency import Dependency
                            session.add(Dependency(**dep))
                        session.commit()

                elif analyzer.name == "framework-detector":
                    for fw in result.extracted_entities:
                        self.db.save_framework_evidence(
                            repo_id=repo_id,
                            name=fw["name"],
                            evidence={"version": fw.get("version"), **fw.get("evidence", {})}
                        )

            yield PipelineProgress("analyze", f"Analyzer '{analyzer.name}' complete", 80.0)
            await asyncio.sleep(0)

        # --- Stage 5: Done ---
        elapsed = time.monotonic() - start
        yield PipelineProgress("complete", f"Analysis complete in {elapsed:.1f}s", 100.0)

    def _collect_files(self, repo_path: Path) -> list[tuple[Path, Path, str]]:
        """Walk the repo and return (abs_path, rel_path, language) tuples."""
        results = []
        for abs_path in repo_path.rglob("*"):
            if not abs_path.is_file():
                continue
            if any(d in abs_path.parts for d in SKIP_DIRS):
                continue
            lang = EXTENSION_TO_LANGUAGE.get(abs_path.suffix)
            if lang:
                rel_path = abs_path.relative_to(repo_path)
                results.append((abs_path, rel_path, lang))
        return results
