"""Tests for LanguageDetector."""

from __future__ import annotations

from pathlib import Path

from git_reverse.analysis.language import LanguageDetector
from git_reverse.ingestion.validator import FileManifest


def test_detect_python_primary(tmp_path: Path) -> None:
    detector = LanguageDetector()
    manifest = FileManifest(
        source_files=[
            tmp_path / "app.py",
            tmp_path / "main.py",
            tmp_path / "test.js",  # Secondary
        ]
    )
    profile = detector.detect(manifest, tmp_path)
    assert profile.primary == "python"
    assert "javascript" in profile.secondary
    assert profile.file_counts["python"] == 2
    assert profile.file_counts["javascript"] == 1


def test_detect_frameworks_from_config(tmp_path: Path) -> None:
    detector = LanguageDetector()
    manifest = FileManifest(
        source_files=[tmp_path / "app.py"],
        config_files=[tmp_path / "manage.py"],  # Django signature
    )
    profile = detector.detect(manifest, tmp_path)
    assert profile.primary == "python"
    assert "django" in profile.frameworks.get("python", [])


def test_detect_no_files_returns_unknown(tmp_path: Path) -> None:
    detector = LanguageDetector()
    manifest = FileManifest()
    profile = detector.detect(manifest, tmp_path)
    assert profile.primary == "unknown"
