"""Tests for Python parser."""

from __future__ import annotations

from pathlib import Path

from git_reverse.analysis.parsers.python import PythonParser


def test_parse_python_file(tmp_path: Path) -> None:
    code = """
import os
from datetime import datetime

@dataclass
class User(BaseUser):
    name: str

    def get_name(self):
        return self.name

def main():
    u = User("Chethan")
    print(u.get_name())
"""
    file_path = tmp_path / "test.py"
    file_path.write_text(code, encoding="utf-8")

    parser = PythonParser()
    res = parser.parse(file_path)

    assert res.success
    assert res.language == "python"
    
    # Verify module name
    assert res.symbols[0].type == "module"
    assert res.symbols[0].name == "test"

    # Classes
    classes = [s for s in res.symbols if s.type == "class"]
    assert len(classes) == 1
    assert classes[0].name == "User"
    assert "BaseUser" in classes[0].bases

    # Functions
    funcs = [s for s in res.symbols if s.type == "function"]
    assert len(funcs) == 2
    func_names = {f.name for f in funcs}
    assert "get_name" in func_names
    assert "main" in func_names
