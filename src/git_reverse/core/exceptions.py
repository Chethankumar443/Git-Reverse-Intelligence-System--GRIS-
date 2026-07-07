"""
Structured exception hierarchy for Git Reverse.

Design principles:
  - Every exception carries a `user_message` safe to display in the TUI.
  - Every exception carries a `recoverable` flag that signals whether
    the pipeline can continue (skip + log) or must abort.
  - Internal details (tracebacks, raw OS errors) are kept in `__cause__`
    and logged at DEBUG level — never shown to the user.
"""

from __future__ import annotations


class GitReverseError(Exception):
    """
    Base class for all Git Reverse exceptions.

    All custom exceptions must subclass this so callers can use a
    single `except GitReverseError` guard at the top level.
    """

    def __init__(
        self,
        message: str,
        *,
        user_message: str | None = None,
        recoverable: bool = False,
    ) -> None:
        super().__init__(message)
        self.user_message: str = user_message or message
        self.recoverable: bool = recoverable


# ── Configuration ─────────────────────────────────────────────────────────────
class ConfigurationError(GitReverseError):
    """Raised when settings are invalid or missing required values."""

    def __init__(self, message: str, *, field: str | None = None) -> None:
        super().__init__(
            message,
            user_message=f"Configuration error{f' (field: {field})' if field else ''}: {message}",
            recoverable=False,
        )
        self.field = field


class MissingCredentialError(ConfigurationError):
    """Raised when a required API key or token is not present."""

    def __init__(self, credential_name: str) -> None:
        super().__init__(
            f"Required credential '{credential_name}' is not configured.",
            field=credential_name,
        )
        self.credential_name = credential_name


# ── Ingestion / Git ───────────────────────────────────────────────────────────
class IngestionError(GitReverseError):
    """Base class for repository ingestion failures."""


class RepositoryCloneError(IngestionError):
    """Raised when a git clone operation fails."""

    def __init__(self, url: str, reason: str) -> None:
        super().__init__(
            f"Failed to clone '{url}': {reason}",
            user_message=f"Could not clone repository. Reason: {reason}",
            recoverable=False,
        )
        self.url = url
        self.reason = reason


class RepositoryTooLargeError(IngestionError):
    """Raised when the target repository exceeds the configured size limit."""

    def __init__(self, url: str, size_mb: float, limit_mb: int) -> None:
        super().__init__(
            f"Repository '{url}' is {size_mb:.1f} MB, limit is {limit_mb} MB.",
            user_message=(
                f"Repository is too large ({size_mb:.1f} MB). "
                f"Current limit: {limit_mb} MB. Adjust via /settings."
            ),
            recoverable=False,
        )
        self.size_mb = size_mb
        self.limit_mb = limit_mb


class CloneTimeoutError(IngestionError):
    """Raised when a git clone exceeds the configured timeout."""

    def __init__(self, url: str, timeout_seconds: int) -> None:
        super().__init__(
            f"Clone of '{url}' timed out after {timeout_seconds}s.",
            user_message=f"Clone timed out after {timeout_seconds} seconds.",
            recoverable=False,
        )
        self.timeout_seconds = timeout_seconds


class InvalidRepositoryError(IngestionError):
    """Raised when the target path or URL is not a valid Git repository."""

    def __init__(self, path_or_url: str) -> None:
        super().__init__(
            f"'{path_or_url}' is not a valid Git repository.",
            user_message="The provided path or URL does not appear to be a valid Git repository.",
            recoverable=False,
        )


# ── Analysis / AST ────────────────────────────────────────────────────────────
class AnalysisError(GitReverseError):
    """Base class for analysis pipeline failures."""


class ASTParseError(AnalysisError):
    """
    Raised when tree-sitter fails to parse a specific file.

    This exception is `recoverable=True` — the pipeline logs the failure
    and continues with the remaining files.
    """

    def __init__(self, file_path: str, language: str, reason: str) -> None:
        super().__init__(
            f"AST parse failed for '{file_path}' ({language}): {reason}",
            user_message=f"Could not parse {file_path}. Skipping.",
            recoverable=True,
        )
        self.file_path = file_path
        self.language = language


class UnsupportedLanguageError(AnalysisError):
    """Raised when a file's language has no registered tree-sitter grammar."""

    def __init__(self, language: str) -> None:
        super().__init__(
            f"No tree-sitter grammar registered for language '{language}'.",
            user_message=f"Language '{language}' is not yet supported by the AST parser.",
            recoverable=True,
        )
        self.language = language


class GraphBuildError(AnalysisError):
    """Raised when the knowledge graph construction encounters a fatal error."""

    def __init__(self, reason: str) -> None:
        super().__init__(
            f"Graph construction failed: {reason}",
            user_message="An error occurred while building the knowledge graph.",
            recoverable=False,
        )


# ── Storage ───────────────────────────────────────────────────────────────────
class StorageError(GitReverseError):
    """Base class for database and filesystem errors."""


class DatabaseError(StorageError):
    """Raised when a SQLite operation fails."""

    def __init__(self, operation: str, reason: str) -> None:
        super().__init__(
            f"Database operation '{operation}' failed: {reason}",
            user_message="A database error occurred. Check logs for details.",
            recoverable=False,
        )
        self.operation = operation


class SessionNotFoundError(StorageError):
    """Raised when a requested session ID does not exist."""

    def __init__(self, session_id: str) -> None:
        super().__init__(
            f"Session '{session_id}' not found.",
            user_message=f"No session found with ID '{session_id}'.",
            recoverable=False,
        )
        self.session_id = session_id


# ── Plugin / Skill System ─────────────────────────────────────────────────────
class PluginError(GitReverseError):
    """Base class for plugin/skill system errors."""


class PluginLoadError(PluginError):
    """Raised when a skill manifest cannot be loaded or validated."""

    def __init__(self, plugin_name: str, reason: str) -> None:
        super().__init__(
            f"Failed to load plugin '{plugin_name}': {reason}",
            user_message=f"Plugin '{plugin_name}' could not be loaded. It will be skipped.",
            recoverable=True,
        )
        self.plugin_name = plugin_name


# ── LLM / API ────────────────────────────────────────────────────────────────
class LLMError(GitReverseError):
    """Base class for LLM and API errors."""


class RateLimitError(LLMError):
    """Raised when the LLM provider returns a 429 Too Many Requests."""

    def __init__(self, retry_after_seconds: float | None = None) -> None:
        msg = "OpenRouter rate limit reached."
        hint = (
            f" Retry after {retry_after_seconds:.0f}s."
            if retry_after_seconds
            else " Please wait before retrying."
        )
        super().__init__(
            msg + hint,
            user_message=msg + hint,
            recoverable=True,
        )
        self.retry_after_seconds = retry_after_seconds


class LLMResponseError(LLMError):
    """Raised when the LLM returns a malformed or unexpected response."""

    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(
            f"LLM API error {status_code}: {detail}",
            user_message=f"The AI provider returned an error (HTTP {status_code}).",
            recoverable=False,
        )
        self.status_code = status_code
