"""
Ignore Rules — Parses .gitignore and .gitreverseignore patterns (PRD §54).

Provides a filter function that accepts a relative file path and returns True
if the file should be excluded from analysis based on the active ignore rules.
"""
import re
from typing import List, Set, Dict


# Directories always excluded regardless of ignore rules
ALWAYS_IGNORED_DIRS: Set[str] = {
    ".git", "node_modules", "__pycache__", ".venv", "venv",
    ".pytest_cache", ".mypy_cache", "dist", "build", "target",
    ".idea", ".vscode", ".next", ".nuxt", "bin", "obj",
}

ALWAYS_IGNORED_EXTENSIONS: Set[str] = {
    ".pyc", ".pyo", ".class", ".o", ".a", ".so", ".dll", ".exe",
    ".bin", ".dat", ".db", ".sqlite", ".wasm",
}


def _gitignore_pattern_to_regex(pattern: str) -> re.Pattern | None:
    """Converts a single gitignore pattern line to a compiled regex.

    Returns None for blank lines or comment lines.
    """
    pattern = pattern.strip()
    if not pattern or pattern.startswith("#"):
        return None

    # Negation patterns (!) not supported in v1 — skip
    if pattern.startswith("!"):
        return None

    # Escape regex special chars except * and ?
    escaped = re.escape(pattern).replace(r"\*\*", ".*").replace(r"\*", "[^/]*").replace(r"\?", "[^/]")

    # If pattern ends with / it's a directory-only pattern
    if escaped.endswith("/"):
        escaped = escaped + ".*"

    # If pattern doesn't contain / it applies to any path component
    if "/" not in pattern:
        regex_str = f"(^|.*/)(?:{escaped})(/.*)?$"
    else:
        regex_str = f"^{escaped}(/.*)?$"

    try:
        return re.compile(regex_str)
    except re.error:
        return None


class IgnoreRules:
    """Manages combined gitignore + .gitreverseignore exclusion rules."""

    def __init__(self):
        self._patterns: List[re.Pattern] = []

    def load_from_content(self, gitignore_content: str = "", gitreverseignore_content: str = ""):
        """Parses ignore rule text and compiles patterns."""
        self._patterns = []
        combined = (gitignore_content or "") + "\n" + (gitreverseignore_content or "")
        for line in combined.splitlines():
            pat = _gitignore_pattern_to_regex(line)
            if pat:
                self._patterns.append(pat)

    def load_from_files_dict(self, files: Dict[str, str]):
        """Loads ignore rules from a files dict {path: content}."""
        gitignore = files.get(".gitignore", "") or files.get("gitignore", "")
        gitreverseignore = files.get(".gitreverseignore", "") or files.get("gitreverseignore", "")
        self.load_from_content(gitignore, gitreverseignore)

    def should_ignore(self, rel_path: str) -> bool:
        """Returns True if the given relative path should be excluded."""
        import os
        parts = rel_path.replace("\\", "/").split("/")

        # Always-ignored directory check
        for part in parts[:-1]:
            if part in ALWAYS_IGNORED_DIRS:
                return True

        # Always-ignored extension check
        ext = os.path.splitext(parts[-1])[1].lower()
        if ext in ALWAYS_IGNORED_EXTENSIONS:
            return True

        # User-defined pattern check
        normalized = rel_path.replace("\\", "/")
        for pat in self._patterns:
            if pat.match(normalized):
                return True

        return False

    def filter_files(self, files: Dict[str, str]) -> Dict[str, str]:
        """Returns a filtered dict excluding all ignored paths."""
        return {path: content for path, content in files.items()
                if not self.should_ignore(path)}


def build_ignore_rules(files: Dict[str, str]) -> IgnoreRules:
    """Convenience function: creates an IgnoreRules instance from a files dict."""
    rules = IgnoreRules()
    rules.load_from_files_dict(files)
    return rules
