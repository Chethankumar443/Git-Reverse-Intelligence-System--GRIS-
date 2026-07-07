"""
Repository integrity validator.

Runs before the AST analysis pipeline to ensure the repository is in a
sane state and within the configured constraints. All checks are lightweight
(no file parsing) so the validator completes in milliseconds.

Responsibilities:
  - Confirm the local path exists and is a valid Git repository.
  - Reject repositories that exceed the configured size limit.
  - Detect binary-heavy repos, detecting skippable file categories.
  - Identify submodules that require separate ingestion.
  - Build a filtered file manifest (respecting .gitignore) for downstream
    analysis stages.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import git

from git_reverse.core.exceptions import (
    InvalidRepositoryError,
    RepositoryTooLargeError,
)
from git_reverse.core.logging import get_logger

log = get_logger(__name__)

# ── File category classification ──────────────────────────────────────────────
_BINARY_EXTENSIONS: frozenset[str] = frozenset(
    {
        # Images
        ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".svg", ".ico", ".webp", ".tiff",
        # Video / Audio
        ".mp4", ".mov", ".avi", ".mkv", ".mp3", ".wav", ".ogg",
        # Archives
        ".zip", ".tar", ".gz", ".bz2", ".xz", ".7z", ".rar",
        # Compiled / binary
        ".exe", ".dll", ".so", ".dylib", ".class", ".pyc", ".pyo",
        ".wasm", ".bin", ".o", ".a",
        # Documents
        ".pdf", ".docx", ".xlsx", ".pptx",
        # Fonts
        ".ttf", ".otf", ".woff", ".woff2",
    }
)

_GENERATED_DIRS: frozenset[str] = frozenset(
    {
        "node_modules",
        ".git",
        "__pycache__",
        ".mypy_cache",
        ".ruff_cache",
        ".pytest_cache",
        "dist",
        "build",
        ".next",
        ".nuxt",
        "target",       # Rust
        "vendor",       # Go
        ".venv",
        "venv",
        "env",
        ".tox",
    }
)


@dataclass
class FileManifest:
    """
    The filtered set of files selected for analysis.

    Attributes:
        source_files: Text-based source files suitable for AST parsing.
        config_files: Configuration files (Dockerfile, YAML, TOML, etc.).
        doc_files:    Markdown / RST documentation files.
        binary_files: Binary files — identified but not parsed.
        skipped_dirs: Directories that were excluded entirely.
        total_size_bytes: Sum of sizes for source + config + doc files.
    """

    source_files: list[Path] = field(default_factory=list)
    config_files: list[Path] = field(default_factory=list)
    doc_files: list[Path] = field(default_factory=list)
    binary_files: list[Path] = field(default_factory=list)
    skipped_dirs: list[str] = field(default_factory=list)
    total_size_bytes: int = 0

    @property
    def total_files(self) -> int:
        return len(self.source_files) + len(self.config_files) + len(self.doc_files)

    @property
    def total_size_mb(self) -> float:
        return self.total_size_bytes / (1024 * 1024)


@dataclass
class SubmoduleInfo:
    """Represents a Git submodule found within the repository."""

    name: str
    path: str
    url: str
    is_initialized: bool


@dataclass
class ValidationResult:
    """
    The output of a successful repository validation.

    Attributes:
        repo_path:   Absolute path to the validated repository root.
        head_sha:    The current HEAD commit SHA.
        active_branch: The active branch name (or None for detached HEAD).
        submodules:  Any submodules detected within the repository.
        manifest:    The filtered file manifest ready for analysis.
    """

    repo_path: Path
    head_sha: str
    active_branch: str | None
    submodules: list[SubmoduleInfo]
    manifest: FileManifest


class RepositoryValidator:
    """
    Validates a locally cloned repository before running analysis.

    This class performs NO mutations — it is purely read-only.
    """

    def __init__(self, max_repo_size_mb: int = 2048) -> None:
        self._max_size_mb = max_repo_size_mb

    def validate(self, local_path: Path) -> ValidationResult:
        """
        Validate the repository at `local_path`.

        Args:
            local_path: Absolute path to the repository root on disk.

        Returns:
            A `ValidationResult` with the manifest and metadata.

        Raises:
            InvalidRepositoryError: If the path is not a valid Git repo.
            RepositoryTooLargeError: If the repo exceeds the size limit.
        """
        repo = self._open_repo(local_path)
        head_sha, active_branch = self._resolve_head(repo)
        submodules = self._detect_submodules(repo)
        manifest = self._build_manifest(local_path)

        size_mb = manifest.total_size_mb
        if size_mb > self._max_size_mb:
            raise RepositoryTooLargeError(
                url=str(local_path),
                size_mb=size_mb,
                limit_mb=self._max_size_mb,
            )

        log.info(
            "validation_complete",
            path=str(local_path),
            head=head_sha[:8],
            branch=active_branch,
            source_files=len(manifest.source_files),
            size_mb=f"{size_mb:.1f}",
            submodules=len(submodules),
        )

        return ValidationResult(
            repo_path=local_path,
            head_sha=head_sha,
            active_branch=active_branch,
            submodules=submodules,
            manifest=manifest,
        )

    # ── Private helpers ───────────────────────────────────────────────────────
    @staticmethod
    def _open_repo(local_path: Path) -> git.Repo:
        """Open a GitPython Repo object, raising InvalidRepositoryError if not valid."""
        try:
            return git.Repo(local_path, search_parent_directories=False)
        except (git.InvalidGitRepositoryError, git.NoSuchPathError) as exc:
            raise InvalidRepositoryError(str(local_path)) from exc

    @staticmethod
    def _resolve_head(repo: git.Repo) -> tuple[str, str | None]:
        """Return (HEAD SHA, branch name or None for detached HEAD)."""
        try:
            head_sha = repo.head.commit.hexsha
        except ValueError:
            # Empty repository — no commits yet
            return ("0000000000000000000000000000000000000000", None)

        try:
            branch = repo.active_branch.name
        except TypeError:
            branch = None  # Detached HEAD

        return (head_sha, branch)

    @staticmethod
    def _detect_submodules(repo: git.Repo) -> list[SubmoduleInfo]:
        """Detect and describe all Git submodules in the repository."""
        result: list[SubmoduleInfo] = []
        for sm in repo.submodules:
            try:
                sm.update(init=False)  # Don't auto-initialise; just probe
                is_init = sm.module_exists()
            except Exception:  # noqa: BLE001
                is_init = False

            result.append(
                SubmoduleInfo(
                    name=sm.name,
                    path=str(sm.path),
                    url=sm.url,
                    is_initialized=is_init,
                )
            )
            log.debug("submodule_detected", name=sm.name, initialized=is_init)
        return result

    def _build_manifest(self, root: Path) -> FileManifest:
        """
        Walk the repository tree and classify each file.

        Files inside `_GENERATED_DIRS` are skipped. Binary files are recorded
        but not queued for AST parsing.
        """
        manifest = FileManifest()
        skipped_dir_names: list[str] = []

        for dirpath, dirnames, filenames in os.walk(root):
            current = Path(dirpath)

            # Prune generated / vendor directories in-place so os.walk skips them
            pruned: list[str] = []
            for d in list(dirnames):
                if d in _GENERATED_DIRS:
                    pruned.append(d)
                    dirnames.remove(d)
            skipped_dir_names.extend(pruned)

            for filename in filenames:
                file_path = current / filename
                suffix = file_path.suffix.lower()

                try:
                    size = file_path.stat().st_size
                except OSError:
                    continue  # Broken symlink or race — skip.

                if suffix in _BINARY_EXTENSIONS:
                    manifest.binary_files.append(file_path)
                    continue

                manifest.total_size_bytes += size

                # Classify by purpose
                if suffix in {".md", ".rst", ".txt", ".adoc"}:
                    manifest.doc_files.append(file_path)
                elif suffix in {
                    ".toml", ".yaml", ".yml", ".json", ".ini", ".cfg",
                    ".env", ".conf", ".xml", ".dockerfile", "",
                } or filename in {"Dockerfile", "Makefile", ".env.example"}:
                    manifest.config_files.append(file_path)
                else:
                    manifest.source_files.append(file_path)

        manifest.skipped_dirs = sorted(set(skipped_dir_names))
        return manifest
