"""
Tests for AppSettings — config loading, validation, directory creation,
and worker count resolution.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from git_reverse.config.settings import AppSettings, get_settings


class TestAppSettings:
    """Validate Pydantic field constraints and computed properties."""

    def test_directories_created_on_init(self, tmp_path: Path) -> None:
        """AppSettings must create data and cache directories on initialisation."""
        s = AppSettings(
            data_dir=tmp_path / "data",
            cache_dir=tmp_path / "cache",
        )
        assert s.data_dir.exists()
        assert s.cache_dir.exists()
        assert (s.data_dir / "exports").exists()
        assert (s.data_dir / "skills").exists()

    def test_db_path_is_inside_data_dir(self, settings: AppSettings) -> None:
        assert settings.db_path.parent == settings.data_dir

    def test_repos_cache_path_is_inside_cache_dir(self, settings: AppSettings) -> None:
        assert settings.repos_cache_path.parent == settings.cache_dir

    def test_log_level_normalised_to_uppercase(self, tmp_path: Path) -> None:
        s = AppSettings(data_dir=tmp_path / "d", cache_dir=tmp_path / "c", log_level="debug")
        assert s.log_level == "DEBUG"

    def test_invalid_log_level_raises(self, tmp_path: Path) -> None:
        with pytest.raises(Exception):  # pydantic ValidationError
            AppSettings(
                data_dir=tmp_path / "d",
                cache_dir=tmp_path / "c",
                log_level="VERBOSE",
            )

    def test_analysis_workers_auto_resolves(self, tmp_path: Path) -> None:
        s = AppSettings(
            data_dir=tmp_path / "d",
            cache_dir=tmp_path / "c",
            analysis_workers=0,
        )
        # effective_workers must be ≥ 1 regardless of CPU count
        assert s.effective_workers >= 1

    def test_analysis_workers_explicit(self, tmp_path: Path) -> None:
        s = AppSettings(
            data_dir=tmp_path / "d",
            cache_dir=tmp_path / "c",
            analysis_workers=4,
        )
        assert s.effective_workers == 4

    def test_analysis_workers_max_limit(self, tmp_path: Path) -> None:
        with pytest.raises(Exception):
            AppSettings.model_validate(
                {
                    "data_dir": str(tmp_path / "d"),
                    "cache_dir": str(tmp_path / "c"),
                    "analysis_workers": 100,  # violates le=32 — runtime raises
                }
            )

    def test_has_openrouter_key_false_when_absent(self, settings: AppSettings) -> None:
        # No key configured in the fixture
        assert not settings.has_openrouter_key()

    def test_get_settings_returns_singleton(self, tmp_path: Path) -> None:
        get_settings.cache_clear()
        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2
        get_settings.cache_clear()

    def test_save_and_load_config_json(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Verify that save_settings() saves to json, and AppSettings loads it."""
        # Mock _default_data_dir to point to tmp_path
        from git_reverse.config import settings
        monkeypatch.setattr(settings, "_default_data_dir", lambda: tmp_path)

        s1 = AppSettings(data_dir=tmp_path, cache_dir=tmp_path / "c")
        s1.username = "chethan_test"
        s1.default_model = "test-free-model"
        s1.save_settings()

        # Config file should be created
        config_path = tmp_path / "config.json"
        assert config_path.exists()

        # Instantiate a new settings object, it should load from config.json automatically
        s2 = AppSettings(data_dir=tmp_path, cache_dir=tmp_path / "c")
        assert s2.username == "chethan_test"
        assert s2.default_model == "test-free-model"
