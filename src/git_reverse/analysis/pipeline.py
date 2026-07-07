"""
Repository AST Analysis Pipeline.

Orchestrates the entire Phase 2 processing sequence:
  1. Detects primary/secondary languages and frameworks.
  2. Parses files concurrently using a worker pool.
  3. Computes complexity scores for functions.
  4. Builds the dependency graph in memory.
  5. Persists the graph (nodes & edges) into SQLite.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable, Coroutine
from pathlib import Path
from typing import Any

from git_reverse.analysis.complexity import ComplexityScorer
from git_reverse.analysis.graph import KnowledgeGraphBuilder
from git_reverse.analysis.language import LanguageDetector
from git_reverse.analysis.parsers.registry import ParserRegistry
from git_reverse.core.events import (
    AnalysisPipelineCompleteEvent,
    ASTParseCompletedEvent,
    ASTParseFailedEvent,
    EventBus,
    GraphConstructedEvent,
    get_event_bus,
)
from git_reverse.core.logging import get_logger
from git_reverse.ingestion.validator import ValidationResult
from git_reverse.storage.database import Database, RepositoryDAO

log = get_logger(__name__)

# Progress callback signature: (phase, completed, total, message) -> None
PipelineProgressCallback = Callable[[str, int, int, str], Coroutine[Any, Any, None]]


class AnalysisPipeline:
    """Orchestrates the full parsing and graph generation pipeline."""

    def __init__(
        self,
        db: Database,
        bus: EventBus | None = None,
        max_workers: int = 4,
    ) -> None:
        self._db = db
        self._bus = bus or get_event_bus()
        self._max_workers = max_workers
        self._registry = ParserRegistry()

    async def run(
        self,
        repo_id: str,
        validation_result: ValidationResult,
        progress_callback: PipelineProgressCallback | None = None,
    ) -> None:
        """
        Execute the analysis pipeline.

        Args:
            repo_id:           The database ID of the repository.
            validation_result: The result of validation containing the file manifest.
            progress_callback: Optional async progress updates reporter.
        """
        start_time = time.monotonic()
        manifest = validation_result.manifest
        repo_path = validation_result.repo_path

        # ── Step 1: Detect Languages & Frameworks ─────────────────────────────
        if progress_callback:
            await progress_callback("detecting_languages", 0, 100, "Detecting languages...")

        detector = LanguageDetector()
        profile = detector.detect(manifest, repo_path)

        # Save primary language to Repository record
        repo_dao = RepositoryDAO(self._db)
        repo_record = await repo_dao.get_by_id(repo_id)
        if repo_record:
            repo_record.primary_language = profile.primary
            repo_record.metadata = repo_record.metadata or {}
            repo_record.metadata["frameworks"] = profile.frameworks
            await repo_dao.upsert(repo_record)

        # ── Step 2: Parse Files Concurrently ──────────────────────────────────
        source_files = manifest.source_files
        total_files = len(source_files)
        parsed_symbols = []

        if total_files > 0:
            semaphore = asyncio.Semaphore(self._max_workers)

            async def parse_one(file_path: Path, idx: int) -> list[Any]:
                async with semaphore:
                    parser = self._registry.get_parser(file_path.suffix)
                    if not parser:
                        return []

                    # Run CPU-bound parsing in executor thread
                    loop = asyncio.get_running_loop()
                    res = await loop.run_in_executor(None, parser.parse, file_path)

                    if res.success:
                        # Compute complexity metrics on functions
                        for sym in res.symbols:
                            if sym.type == "function":
                                metrics = ComplexityScorer.score_function(sym.content, res.language)
                                sym.metadata.update(metrics)

                        await self._bus.emit(
                            ASTParseCompletedEvent(
                                repo_id=repo_id,
                                file_path=res.file_path,
                                language=res.language,
                                node_count=res.node_count,
                            )
                        )
                        if progress_callback:
                            await progress_callback(
                                "parsing",
                                idx + 1,
                                total_files,
                                f"Parsed {file_path.name}",
                            )
                        return res.symbols
                    else:
                        await self._bus.emit(
                            ASTParseFailedEvent(
                                repo_id=repo_id,
                                file_path=res.file_path,
                                language=res.language,
                                reason=res.error or "Unknown error",
                            )
                        )
                        return []

            tasks = [parse_one(f, i) for i, f in enumerate(source_files)]
            results = await asyncio.gather(*tasks)
            for res_list in results:
                parsed_symbols.extend(res_list)

        # ── Step 3: Construct Dependency Graph ──────────────────────────────
        if progress_callback:
            await progress_callback("graphing", 90, 100, "Constructing dependency graph...")

        builder = KnowledgeGraphBuilder()
        graph = builder.build(parsed_symbols)

        await self._bus.emit(
            GraphConstructedEvent(
                repo_id=repo_id,
                node_count=graph.number_of_nodes(),
                edge_count=graph.number_of_edges(),
            )
        )

        # ── Step 4: Persist to Database ───────────────────────────────────────
        if progress_callback:
            await progress_callback("persisting", 95, 100, "Saving database index...")

        # Write nodes and edges within transaction
        async with self._db.transaction():
            # Clear old records for this repository if any exist
            await self._db.conn.execute("DELETE FROM edges WHERE source_id IN (SELECT id FROM nodes WHERE repo_id = ?)", (repo_id,))
            await self._db.conn.execute("DELETE FROM nodes WHERE repo_id = ?", (repo_id,))

            # Insert Nodes
            node_insert_sql = """
                INSERT INTO nodes (id, repo_id, type, name, file_path, start_line, end_line, content, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            for node_id, attrs in graph.nodes(data=True):
                # Resolve content from original symbols list to save database space
                content_val = next((s.content for s in parsed_symbols if s.id == node_id), None)

                # Copy properties out to avoid extra payload inside metadata json
                node_type = attrs.get("type", "unknown")
                name = attrs.get("name", "unknown")
                file_path = attrs.get("file_path")
                start_line = attrs.get("start_line")
                end_line = attrs.get("end_line")

                meta_json = "{}"
                # Filter out base keys from metadata payload
                meta_filtered = {k: v for k, v in attrs.items() if k not in ("type", "name", "file_path", "start_line", "end_line")}
                import json
                meta_json = json.dumps(meta_filtered)

                await self._db.conn.execute(
                    node_insert_sql,
                    (node_id, repo_id, node_type, name, file_path, start_line, end_line, content_val, meta_json)
                )

            # Insert Edges
            edge_insert_sql = """
                INSERT INTO edges (source_id, target_id, relation_type, metadata)
                VALUES (?, ?, ?, ?)
            """
            for u, v, attrs in graph.edges(data=True):
                rel = attrs.get("relation", "dependency")
                await self._db.conn.execute(edge_insert_sql, (u, v, rel, "{}"))

        duration = time.monotonic() - start_time
        await self._bus.emit(AnalysisPipelineCompleteEvent(repo_id=repo_id, duration_seconds=duration))

        if progress_callback:
            await progress_callback("complete", 100, 100, "Analysis complete.")

        log.info(
            "pipeline_finished",
            repo_id=repo_id,
            nodes=graph.number_of_nodes(),
            edges=graph.number_of_edges(),
            duration=f"{duration:.2f}s",
        )
