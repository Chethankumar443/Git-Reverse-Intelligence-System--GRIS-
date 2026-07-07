"""
Shared pytest fixtures and configuration.

Fixtures in this file are automatically available to all test modules.
Conventions:
  - Use `tmp_path` (pytest built-in) for temporary directories.
  - Use `settings` fixture for a fresh AppSettings with overridden paths.
  - Use `db` fixture for a connected in-memory / temp-file Database.
  - Use `event_bus` fixture for a clean EventBus with no registered handlers.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator, Generator
from pathlib import Path

import pytest
import pytest_asyncio

from git_reverse.config.settings import AppSettings, get_settings
from git_reverse.core.events import EventBus, reset_event_bus
from git_reverse.storage.database import Database




# ── Settings ──────────────────────────────────────────────────────────────────
@pytest.fixture
def settings(tmp_path: Path) -> AppSettings:
    """
    Return a fresh AppSettings instance wired to a temp directory.

    Clears the lru_cache so every test gets an isolated settings object.
    """
    get_settings.cache_clear()
    return AppSettings(
        data_dir=tmp_path / "data",
        cache_dir=tmp_path / "cache",
        log_level="DEBUG",
        dev_mode=True,
        default_model="openai/gpt-4o-mini",
        analysis_workers=2,
    )


# ── Database ──────────────────────────────────────────────────────────────────
@pytest_asyncio.fixture
async def db(settings: AppSettings) -> AsyncGenerator[Database, None]:
    """
    Provide a fully migrated, connected Database using a temp SQLite file.

    The database is closed automatically after the test.
    """
    database = Database(settings.db_path)
    await database.connect()
    yield database
    await database.close()


# ── Event Bus ─────────────────────────────────────────────────────────────────
@pytest.fixture
def event_bus() -> Generator[EventBus, None, None]:
    """
    Provide a clean EventBus with no pre-registered handlers.

    Resets the global singleton before and after each test.
    """
    reset_event_bus()
    bus = EventBus()
    yield bus
    reset_event_bus()


# ── Git repo factory ──────────────────────────────────────────────────────────
@pytest.fixture
def make_git_repo(tmp_path: Path):
    """
    Factory fixture that creates minimal local Git repositories for testing.

    Usage:
        def test_something(make_git_repo):
            repo_path = make_git_repo("my-project", files={"src/main.py": "print('hello')"})
    """
    import git as gitpython

    def _factory(
        name: str = "test-repo",
        files: dict[str, str] | None = None,
    ) -> Path:
        repo_path = tmp_path / name
        repo_path.mkdir(parents=True, exist_ok=True)
        repo = gitpython.Repo.init(repo_path)

        # Configure identity so git commit works in CI
        repo.config_writer().set_value("user", "name", "Test User").release()
        repo.config_writer().set_value("user", "email", "test@example.com").release()

        default_files = files or {
            "README.md": f"# {name}\n\nTest repository.\n",
            "src/__init__.py": "",
            "src/main.py": 'def main() -> None:\n    print("hello")\n',
            "pyproject.toml": '[project]\nname = "test"\nversion = "0.1.0"\n',
        }

        for relative_path, content in default_files.items():
            file_path = repo_path / relative_path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding="utf-8")

        repo.index.add(list(default_files.keys()))
        repo.index.commit("Initial commit")
        return repo_path

    return _factory
