"""Tests for KnowledgeGraphBuilder."""

from __future__ import annotations

from git_reverse.analysis.graph import KnowledgeGraphBuilder
from git_reverse.analysis.parsers.base import ParsedSymbol


def test_build_dependency_graph() -> None:
    # Set up some symbols with dependency hints
    module_sym = ParsedSymbol(
        id="mod-1",
        type="module",
        name="test_mod",
        file_path="test_mod.py",
    )
    class_sym = ParsedSymbol(
        id="class-1",
        type="class",
        name="Calculator",
        file_path="test_mod.py",
        start_line=5,
        end_line=20,
        bases=["BaseCalculator"],
    )
    func_sym = ParsedSymbol(
        id="func-1",
        type="function",
        name="add",
        file_path="test_mod.py",
        start_line=8,
        end_line=12,
        calls=["helper_func"],
    )
    helper_sym = ParsedSymbol(
        id="func-2",
        type="function",
        name="helper_func",
        file_path="test_mod.py",
        start_line=25,
        end_line=30,
    )

    symbols = [module_sym, class_sym, func_sym, helper_sym]
    
    builder = KnowledgeGraphBuilder()
    graph = builder.build(symbols)

    assert graph.number_of_nodes() == 4
    
    # Verify contains (Calculator is inside module, add function is inside Calculator class)
    assert graph.has_edge("mod-1", "class-1")
    assert graph.get_edge_data("mod-1", "class-1")["relation"] == "contains"
    assert graph.has_edge("class-1", "func-1")

    # Verify calls (add function calls helper_func)
    assert graph.has_edge("func-1", "func-2")
    assert graph.get_edge_data("func-1", "func-2")["relation"] == "calls"
