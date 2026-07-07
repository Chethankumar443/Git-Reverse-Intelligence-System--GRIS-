"""
Context compiler.

Retrieves repository metadata, file lists, and symbol/source code nodes from SQLite
to construct context payloads for LLM reasoning.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from git_reverse.storage.database import Database


class ContextCompiler:
    """Queries SQLite and compiles context strings for the LLM."""

    def __init__(self, db: Database) -> None:
        self._db = db

    async def compile_context(self, repo_id: str, query: str | None = None) -> str:
        """
        Compile context for a repository.

        If a query is provided, performs symbol ranking and gathers matching
        source files and call relationships.
        If no query is provided, compiles a high-level codebase skeletal map.
        """
        # 1. Fetch Repository Metadata
        async with self._db.conn.execute(
            "SELECT * FROM repositories WHERE id = ?", (repo_id,)
        ) as cursor:
            repo_row = await cursor.fetchone()
        
        if not repo_row:
            return "No repository found."

        repo_dict = dict(repo_row)
        meta = json.loads(repo_dict.get("metadata") or "{}")
        frameworks = meta.get("frameworks", {})
        
        # 2. Get high-level file list
        async with self._db.conn.execute(
            "SELECT file_path, type, name FROM nodes WHERE repo_id = ? AND type = 'module' ORDER BY file_path",
            (repo_id,),
        ) as cursor:
            files_rows = list(await cursor.fetchall())

        # Compile header details
        lines = [
            f"Repository Name: {repo_dict['name']}",
            f"Primary Language: {repo_dict['primary_language']}",
            f"Detected Frameworks: {json.dumps(frameworks)}",
            "\nFiles Present in Repository:",
        ]
        for f in files_rows:
            lines.append(f"  - {f['file_path']}")

        # 3. If query is provided, search matching symbols to embed content
        if query:
            # Simple keyword match in name/content for ranking
            keywords = [w.lower() for w in query.split() if len(w) > 2]
            
            # Retrieve node symbols
            async with self._db.conn.execute(
                "SELECT * FROM nodes WHERE repo_id = ? AND type != 'module'",
                (repo_id,),
            ) as cursor:
                nodes_rows = list(await cursor.fetchall())

            matching_nodes = []
            for node in nodes_rows:
                node_name = node["name"].lower()
                node_content = (node["content"] or "").lower()
                
                score = 0
                for kw in keywords:
                    if kw in node_name:
                        score += 10
                    if kw in node_content:
                        score += 2
                
                if score > 0:
                    matching_nodes.append((score, node))

            # Sort by score descending and take top 5
            matching_nodes.sort(key=lambda x: x[0], reverse=True)
            top_nodes = [node for _, node in matching_nodes[:5]]

            if top_nodes:
                lines.append("\nRelevant Code Snippets & Symbols:")
                for n in top_nodes:
                    lines.append(f"\n--- Symbol: {n['name']} ({n['type']}) in {n['file_path']} ---")
                    lines.append(n["content"] or "")
                    
                    # Embed metadata metrics if cyclomatic complexity is found
                    n_meta = json.loads(n["metadata"] or "{}")
                    if "complexity" in n_meta:
                        lines.append(
                            f"# Metrics: complexity={n_meta['complexity']}, "
                            f"loc={n_meta['loc']}, depth={n_meta['depth']}"
                        )
        else:
            # Summarized structure overview
            async with self._db.conn.execute(
                "SELECT * FROM nodes WHERE repo_id = ? AND type IN ('class', 'struct', 'trait') LIMIT 20",
                (repo_id,),
            ) as cursor:
                structures = list(await cursor.fetchall())
            
            if structures:
                lines.append("\nCodebase Structures (Classes / Structs):")
                for s in structures:
                    lines.append(f"  - {s['name']} ({s['type']}) in {s['file_path']}")

        return "\n".join(lines)
