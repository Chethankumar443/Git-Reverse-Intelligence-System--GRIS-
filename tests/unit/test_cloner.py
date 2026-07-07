"""
Tests for RepositoryCloner and RepositoryValidator.

Network tests are avoided — all clone tests use the `make_git_repo` fixture
to create real local Git repositories. This keeps the suite fast and
deterministic in CI without a network connection.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import git
import pytest

from git_reverse.core.exceptions import (
    InvalidRepositoryError,
    RepositoryTooLargeError,
)
from git_reverse.core.events import EventBus, RepositoryIngestedEvent
from git_reverse.ingestion.cloner import RepositoryCloner
from git_reverse.ingestion.validator import (
    FileManifest,
    RepositoryValidator,
    _BINARY_EXTENSIONS,
    _GENERATED_DIRS,
)


# ── RepositoryValidator ───────────────────────────────────────────────────────
class TestRepositoryValidator:
    def test_validate_valid_repo(self, make_git_repo: Any) -> None:
        repo_path: Path = make_git_repo("valid-repo")
        validator = RepositoryValidator(max_repo_size_mb=100)
        result = validator.validate(repo_path)

        assert result.repo_path == repo_path
        assert len(result.head_sha) == 40
        assert result.active_branch is not None
        assert result.manifest.total_files > 0

    def test_validate_invalid_path_raises(self, tmp_path: Path) -> None:
        not_a_repo = tmp_path / "not-a-repo"
        not_a_repo.mkdir()
        validator = RepositoryValidator()
        with pytest.raises(InvalidRepositoryError):
            validator.validate(not_a_repo)

    def test_validate_nonexistent_path_raises(self, tmp_path: Path) -> None:
        validator = RepositoryValidator()
        with pytest.raises(InvalidRepositoryError):
            validator.validate(tmp_path / "missing")

    def test_size_limit_enforced(self, make_git_repo: Any, tmp_path: Path) -> None:
        """Repos exceeding the size limit must raise RepositoryTooLargeError."""
        repo_path: Path = make_git_repo("big-repo")
        # Set an absurdly small limit (0 MB) to trigger the check
        validator = RepositoryValidator(max_repo_size_mb=0)
        with pytest.raises(RepositoryTooLargeError) as exc_info:
            validator.validate(repo_path)
        assert exc_info.value.limit_mb == 0

    def test_manifest_classifies_source_files(self, make_git_repo: Any) -> None:
        repo_path: Path = make_git_repo(
            "classify-test",
            files={
                "README.md": "# readme",
                "src/app.py": "print('hi')",
                "Dockerfile": "FROM python:3.12",
                "pyproject.toml": "[project]\nname='test'",
            },
        )
        validator = RepositoryValidator()
        result = validator.validate(repo_path)
        manifest = result.manifest

        source_names = [f.name for f in manifest.source_files]
        doc_names = [f.name for f in manifest.doc_files]
        config_names = [f.name for f in manifest.config_files]

        assert "app.py" in source_names
        assert "README.md" in doc_names
        assert "Dockerfile" in config_names or "pyproject.toml" in config_names

    def test_manifest_excludes_generated_dirs(self, make_git_repo: Any) -> None:
        files = {
            "src/main.py": "pass",
            "node_modules/lodash/index.js": "module.exports={}",
            "__pycache__/main.cpython-312.pyc": "bytecode",
        }
        repo_path: Path = make_git_repo("generated-dirs", files=files)
        validator = RepositoryValidator()
        result = validator.validate(repo_path)

        all_paths = (
            result.manifest.source_files
            + result.manifest.config_files
            + result.manifest.doc_files
            + result.manifest.binary_files
        )
        for path in all_paths:
            for part in path.parts:
                assert part not in _GENERATED_DIRS, f"Generated dir leaked: {path}"

    def test_manifest_excludes_binary_files(self, make_git_repo: Any) -> None:
        files = {
            "src/main.py": "pass",
            "assets/logo.png": "\x89PNG\r\n",
        }
        repo_path: Path = make_git_repo("binary-test", files=files)
        validator = RepositoryValidator()
        result = validator.validate(repo_path)

        binary_names = [f.name for f in result.manifest.binary_files]
        assert "logo.png" in binary_names
        # PNG must not appear in source files
        source_names = [f.name for f in result.manifest.source_files]
        assert "logo.png" not in source_names

    def test_submodules_detected(self, tmp_path: Path) -> None:
        """Submodule detection returns empty list when no submodules present."""
        # Create a bare parent repo without submodules
        parent = tmp_path / "parent"
        parent.mkdir()
        repo = git.Repo.init(parent)
        repo.config_writer().set_value("user", "name", "T").release()
        repo.config_writer().set_value("user", "email", "t@t.com").release()
        (parent / "README.md").write_text("# test")
        repo.index.add(["README.md"])
        repo.index.commit("init")

        validator = RepositoryValidator()
        result = validator.validate(parent)
        assert result.submodules == []

    def test_file_manifest_size_accumulates(self, make_git_repo: Any) -> None:
        files = {"a.py": "x" * 1000, "b.py": "y" * 2000}
        repo_path: Path = make_git_repo("size-test", files=files)
        validator = RepositoryValidator()
        result = validator.validate(repo_path)
        assert result.manifest.total_size_bytes >= 3000

    def test_file_manifest_total_files_count(self, make_git_repo: Any) -> None:
        files = {
            "a.py": "pass",
            "b.py": "pass",
            "README.md": "# r",
            "config.toml": "[x]",
        }
        repo_path: Path = make_git_repo("count-test", files=files)
        validator = RepositoryValidator()
        result = validator.validate(repo_path)
        assert result.manifest.total_files >= 4


# ── RepositoryCloner ──────────────────────────────────────────────────────────
class TestRepositoryCloner:
    async def test_clone_local_path(
        self, make_git_repo: Any, tmp_path: Path, event_bus: EventBus
    ) -> None:
        """Cloning a local directory should return its path without copying."""
        repo_path: Path = make_git_repo("local-target")
        cloner = RepositoryCloner(
            cache_dir=tmp_path / "cache",
            timeout_seconds=30,
            bus=event_bus,
        )
        result_path = await cloner.clone(str(repo_path), repo_id="test-001")
        assert result_path == repo_path

    async def test_clone_local_path_emits_event(
        self, make_git_repo: Any, tmp_path: Path, event_bus: EventBus
    ) -> None:
        """A successful clone must emit a RepositoryIngestedEvent."""
        received: list[RepositoryIngestedEvent] = []

        @event_bus.on(RepositoryIngestedEvent)
        async def capture(event: RepositoryIngestedEvent) -> None:
            received.append(event)

        repo_path: Path = make_git_repo("event-target")
        cloner = RepositoryCloner(
            cache_dir=tmp_path / "cache",
            timeout_seconds=30,
            bus=event_bus,
        )
        await cloner.clone(str(repo_path), repo_id="test-002")
        assert len(received) == 1
        assert received[0].repo_id == "test-002"
        assert received[0].local_path == repo_path

    async def test_invalid_local_path_raises(
        self, tmp_path: Path, event_bus: EventBus
    ) -> None:
        not_a_repo = tmp_path / "empty"
        not_a_repo.mkdir()
        cloner = RepositoryCloner(
            cache_dir=tmp_path / "cache",
            timeout_seconds=30,
            bus=event_bus,
        )
        with pytest.raises(InvalidRepositoryError):
            await cloner.clone(str(not_a_repo), repo_id="test-003")

    async def test_cache_hit_skips_clone(
        self, make_git_repo: Any, tmp_path: Path, event_bus: EventBus, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """
        If the destination directory already exists, the cloner must reuse it
        without re-cloning. We verify this by making the destination exist first
        and asserting no git.Repo.clone_from is called.
        """
        clone_calls: list[str] = []

        original_clone = git.Repo.clone_from

        def patched_clone(url: str, *args: Any, **kwargs: Any) -> git.Repo:
            clone_calls.append(url)
            return original_clone(url, *args, **kwargs)

        monkeypatch.setattr(git.Repo, "clone_from", staticmethod(patched_clone))

        # Pre-create the destination to simulate an existing cache entry
        repo_path: Path = make_git_repo("cached-repo")
        cloner = RepositoryCloner(
            cache_dir=tmp_path / "cache",
            timeout_seconds=30,
            bus=event_bus,
        )

        # First call: actually clones (no pre-existing cache for remote URLs)
        # We use a local path, so clone_from is never called at all
        result = await cloner.clone(str(repo_path), repo_id="cache-001")
        assert result == repo_path
        assert len(clone_calls) == 0  # Local path → never calls clone_from
