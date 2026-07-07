"""Tests for ComplexityScorer."""

from __future__ import annotations

from git_reverse.analysis.complexity import ComplexityScorer


def test_score_simple_function() -> None:
    code = """
def simple():
    print("hello")
"""
    metrics = ComplexityScorer.score_function(code, "python")
    assert metrics["complexity"] == 1
    assert metrics["loc"] == 2
    assert metrics["depth"] == 1


def test_score_complex_function() -> None:
    code = """
def complex_fn(a, b):
    if a > 0:
        for i in range(10):
            if b:
                return i
    elif b:
        return 0
    return -1
"""
    metrics = ComplexityScorer.score_function(code, "python")
    # if, for, if, elif => 4 branch points + 1 = 5
    assert metrics["complexity"] == 5
    assert metrics["loc"] == 8
    assert metrics["depth"] == 4
