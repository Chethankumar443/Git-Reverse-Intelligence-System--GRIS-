"""
Application settings using Pydantic Settings v2.

All sensitive values (API keys) are stored in the OS keychain via the
`keyring` library. Non-sensitive settings are stored in a local config
file and can be overridden by environment variables or a .env file.

Priority (highest → lowest):
  1. Environment variables
  2. .env file
  3. Local config file (~/.config/git-reverse/config.toml or OS equivalent)
  4. Defaults defined here
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import keyring
from platformdirs import user_cache_dir, user_config_dir, user_data_dir
from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# ── Constants ─────────────────────────────────────────────────────────────────
APP_NAME = "git-reverse"
KEYRING_SERVICE = "git-reverse"
KEYRING_OPENROUTER_KEY = "openrouter_api_key"
KEYRING_GITHUB_KEY = "github_api_token"


# ── Directory Helpers ─────────────────────────────────────────────────────────
def _default_data_dir() -> Path:
    return Path(user_data_dir(APP_NAME, ensure_exists=True))


def _default_cache_dir() -> Path:
    return Path(user_cache_dir(APP_NAME, ensure_exists=True))


def _default_config_dir() -> Path:
    return Path(user_config_dir(APP_NAME, ensure_exists=True))


# ── Settings Model ────────────────────────────────────────────────────────────
class AppSettings(BaseSettings):
    """
    Core application settings for Git Reverse.

    Sensitive credentials are never stored in plain text. This class
    reads API keys from environment variables at startup; the CLI
    `onboarding` flow persists them to the OS keychain instead.
    """

    model_config = SettingsConfigDict(
        env_prefix="GIT_REVERSE_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Credentials (env-only; prefer keyring after onboarding) ──────────────
    openrouter_api_key: SecretStr | None = Field(
        default=None,
        description="OpenRouter API key. Use /settings to store securely.",
    )
    github_api_token: SecretStr | None = Field(
        default=None,
        description="GitHub personal access token (optional).",
    )

    # ── Directories ───────────────────────────────────────────────────────────
    data_dir: Path = Field(
        default_factory=_default_data_dir,
        description="Primary data directory for sessions and the SQLite DB.",
    )
    cache_dir: Path = Field(
        default_factory=_default_cache_dir,
        description="Directory for cloned repository caches.",
    )

    # ── LLM Defaults ─────────────────────────────────────────────────────────
    default_model: str = Field(
        default="google/gemini-flash-1.5",
        description="Default OpenRouter model ID.",
    )

    # ── Analysis Engine ───────────────────────────────────────────────────────
    analysis_workers: int = Field(
        default=0,  # 0 = auto-detect from os.cpu_count()
        ge=0,
        le=32,
        description="Parallel workers for AST parsing. 0 = auto.",
    )
    clone_timeout_seconds: int = Field(
        default=300,
        ge=30,
        description="Maximum time in seconds allowed for a git clone.",
    )
    max_repo_size_mb: int = Field(
        default=2048,
        ge=1,
        description="Maximum repository size in MB to accept for analysis.",
    )

    # ── Application Behaviour ─────────────────────────────────────────────────
    log_level: str = Field(default="INFO", description="Logging verbosity.")
    dev_mode: bool = Field(
        default=False,
        description="Enables verbose logging and the TUI dev console.",
    )
    username: str = Field(
        default="",
        description="Display name set during onboarding.",
    )
    theme: str = Field(
        default="midnight",
        description="TUI theme name. Options: midnight | calm.",
    )

    # ── Computed / Derived ────────────────────────────────────────────────────
    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper = v.upper()
        if upper not in allowed:
            raise ValueError(f"log_level must be one of {allowed}, got '{v}'")
        return upper

    @field_validator("analysis_workers")
    @classmethod
    def resolve_workers(cls, v: int) -> int:
        if v == 0:
            return max(1, (os.cpu_count() or 2) - 1)
        return v

    @model_validator(mode="before")
    @classmethod
    def load_from_config_json(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        config_path = _default_data_dir() / "config.json"
        if config_path.exists():
            try:
                import json
                saved = json.loads(config_path.read_text(encoding="utf-8"))
                for key, val in saved.items():
                    if key not in data or data[key] is None or data[key] == "":
                        data[key] = val
            except Exception:
                pass
        return data

    @model_validator(mode="after")
    def ensure_directories_exist(self) -> AppSettings:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        (self.data_dir / "exports").mkdir(parents=True, exist_ok=True)
        (self.data_dir / "skills").mkdir(parents=True, exist_ok=True)
        return self

    def save_settings(self) -> None:
        """Persist non-sensitive configuration settings to config.json."""
        import json
        config_path = self.data_dir / "config.json"
        data = {
            "username": self.username,
            "default_model": self.default_model,
            "theme": self.theme,
            "analysis_workers": self.analysis_workers,
        }
        config_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    # ── Keyring Integration ───────────────────────────────────────────────────
    def get_openrouter_key(self) -> str | None:
        """
        Retrieve the OpenRouter API key.

        Prefers the OS keychain (set during onboarding) over the environment
        variable, so that keys are never stored in plain-text config files.
        """
        # Keychain takes priority
        stored = keyring.get_password(KEYRING_SERVICE, KEYRING_OPENROUTER_KEY)
        if stored:
            return stored
        # Fall back to env-supplied secret
        if self.openrouter_api_key:
            return self.openrouter_api_key.get_secret_value()
        return None

    def save_openrouter_key(self, key: str) -> None:
        """Persist the OpenRouter API key securely to the OS keychain."""
        keyring.set_password(KEYRING_SERVICE, KEYRING_OPENROUTER_KEY, key)

    def get_github_token(self) -> str | None:
        """Retrieve the GitHub token from keychain or env."""
        stored = keyring.get_password(KEYRING_SERVICE, KEYRING_GITHUB_KEY)
        if stored:
            return stored
        if self.github_api_token:
            return self.github_api_token.get_secret_value()
        return None

    def save_github_token(self, token: str) -> None:
        """Persist the GitHub token securely to the OS keychain."""
        keyring.set_password(KEYRING_SERVICE, KEYRING_GITHUB_KEY, token)

    def has_openrouter_key(self) -> bool:
        """Return True if an OpenRouter key is available (keychain or env)."""
        return self.get_openrouter_key() is not None

    @property
    def db_path(self) -> Path:
        """Absolute path to the local SQLite database file."""
        return self.data_dir / "knowledge.db"

    @property
    def repos_cache_path(self) -> Path:
        """Directory where all cloned repositories are cached."""
        return self.cache_dir / "repos"

    @property
    def effective_workers(self) -> int:
        """The resolved (non-zero) worker count."""
        return self.analysis_workers


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    """
    Return the singleton application settings instance.

    Uses `@lru_cache` so the settings object is constructed once and
    reused across all modules. Call `get_settings.cache_clear()` in
    tests to force re-initialisation.
    """
    return AppSettings()
