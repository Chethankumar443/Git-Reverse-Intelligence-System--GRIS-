"""
Cyclomatic complexity and metrics scorer.

Computes cyclomatic complexity, logical lines of code (LOC), and maximum nesting
depth of tree-sitter AST nodes (specifically functions/methods).
"""

from __future__ import annotations

from tree_sitter import Node


class ComplexityScorer:
    """Computes code complexity metrics (cyclomatic complexity, LOC, depth)."""

    @classmethod
    def score_function(cls, node_content: str, language: str) -> dict[str, int]:
        """
        Compute complexity metrics for a function/method code block.
        
        Uses a lightweight tree-sitter independent scoring strategy by walking the
        parsed syntax blocks or counting logical branch keywords.
        """
        # Fallback keyword-based scanner when tree-sitter AST is not directly
        # traversed as full file context, or to keep it fast and language-independent.
        # Counts conditional control structures.
        loc = len([line for line in node_content.splitlines() if line.strip()])
        
        # Branch points: if, elif, for, while, catch/except, &&, ||, case, ?, and, or
        # Standard cyclomatic complexity base is 1.
        complexity = 1
        
        # Word boundaries matching conditional constructs
        import re
        branch_patterns = [
            r"\bif\b", r"\belif\b", r"\bfor\b", r"\bwhile\b", r"\bexcept\b",
            r"\bcatch\b", r"\bcase\b", r"&&", r"\|\|", r"\band\b", r"\bor\b"
        ]
        
        for pattern in branch_patterns:
            complexity += len(re.findall(pattern, node_content))

        # Measure depth based on maximum indentation levels (simple but highly effective TUI metric)
        max_depth = 0
        for line in node_content.splitlines():
            stripped = line.lstrip()
            if stripped:
                indent = len(line) - len(stripped)
                depth = indent // 4  # Standard 4-space indent
                if depth > max_depth:
                    max_depth = depth

        return {
            "complexity": complexity,
            "loc": loc,
            "depth": max_depth,
        }
