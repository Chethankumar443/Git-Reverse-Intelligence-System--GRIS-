"""
Repository cloner — async Git ingestion with progress streaming.

Design:
  - `RepositoryCloner.clone()` is the sole public entry-point.
  - It accepts either a remote URL or a local filesystem path.
  - Clones are cached by URL hash so re-analysing the same repo is instant.
  - Uses `asyncio.to_thread` to run the blocking `git` operations without
    stalling the Textual event loop.
  - Emits progress updates via an async callback so the TUI can render a
    live progress bar.
  - Retry logic handles transient network failures (3 attempts, exponential
    back-off: 2 s, 4 s, 8 s).
  - Respects the configured clone timeout.
"""

from __future__ import annotations

import asyncio
import hashlib
import shutil
import time
from collections.abc import Callable, Coroutine
from pathlib import Path
from typing import Any

import git
from git import RemoteProgress

from git_reverse.core.events import EventBus, RepositoryIngestedEvent, get_event_bus
from git_reverse.core.exceptions import (
    CloneTimeoutError,
    InvalidRepositoryError,
    RepositoryCloneError,
)
from git_reverse.core.logging import get_logger

log = get_logger(__name__)

# Async progress callback signature:  (phase, completed, total, message) -> None
ProgressCallback = Callable[[str, int, int, str], Coroutine[Any, Any, None]]

_MAX_RETRY_ATTEMPTS = 3
_RETRY_BASE_DELAY = 2.0  # seconds


# ── Git progress bridge ───────────────────────────────────────────────────────
class _AsyncProgressBridge(RemoteProgress):
    """
    Bridges GitPython's synchronous RemoteProgress callbacks into the async
    progress callback consumed by the TUI.

    Because this runs in a thread (via asyncio.to_thread), it posts callbacks
    back onto the main event loop using `loop.call_soon_threadsafe`.
    """

    def __init__(
        self,
        loop: asyncio.AbstractEventLoop,
        callback: ProgressCallback | None,
    ) -> None:
        super().__init__()
        self._loop = loop
        self._callback = callback
        self._last_op: str = "initializing"

    def update(
        self,
        op_code: int,
        cur_count: str | float,
        max_count: str | float | None = None,
        message: str = "",
    ) -> None:
        if self._callback is None:
            return
        phase = self._op_to_phase(op_code)
        completed = int(cur_count)
        total = int(max_count) if max_count else 0
        # Schedule the async callback on the main loop from this thread
        coro = self._callback(phase, completed, total, message or phase)
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        # Fire-and-forget; don't block the git thread waiting for the TUI
        future.add_done_callback(lambda f: f.exception() if f.done() and not f.cancelled() else None)

    @staticmethod
    def _op_to_phase(op_code: int) -> str:
        if op_code & RemoteProgress.COUNTING:
            return "Counting objects"
        if op_code & RemoteProgress.COMPRESSING:
            return "Compressing objects"
        if op_code & RemoteProgress.RECEIVING:
            return "Receiving objects"
        if op_code & RemoteProgress.RESOLVING:
            return "Resolving deltas"
        if op_code & RemoteProgress.CHECKING_OUT:
            return "Checking out"
        return "Working"


# ── Cloner ────────────────────────────────────────────────────────────────────
class RepositoryCloner:
    """
    Handles cloning (or opening cached) Git repositories.

    Args:
        cache_dir: The root directory where all repos are cached.
        timeout_seconds: Maximum wall-clock seconds allowed for a clone.
        bus: The application EventBus for emitting lifecycle events.
    """

    def __init__(
        self,
        cache_dir: Path,
        timeout_seconds: int = 300,
        bus: EventBus | None = None,
    ) -> None:
        self._cache_dir = cache_dir
        self._timeout = timeout_seconds
        self._bus = bus or get_event_bus()

    async def clone(
        self,
        url_or_path: str,
        *,
        repo_id: str,
        force_reclone: bool = False,
        progress_callback: ProgressCallback | None = None,
    ) -> Path:
        """
        Clone or retrieve a cached repository.

        Args:
            url_or_path: Remote URL (https / ssh) or local filesystem path.
            repo_id: The database ID assigned to this repository.
            force_reclone: If True, discard any existing cache and re-clone.
            progress_callback: Optional async callable for TUI progress updates.

        Returns:
            The absolute Path to the repository root on disk.

        Raises:
            InvalidRepositoryError: For a local path that isn't a valid repo.
            RepositoryCloneError: If the remote clone fails after retries.
            CloneTimeoutError: If the clone exceeds the configured timeout.
        """
        # ── Local path shortcut ───────────────────────────────────────────────
        local = Path(url_or_path)
        if local.is_dir():
            return await self._open_local(local, repo_id=repo_id)

        # ── Remote URL ────────────────────────────────────────────────────────
        dest = self._destination_for(url_or_path)

        if dest.exists() and not force_reclone:
            log.info("repo_cache_hit", url=url_or_path, dest=str(dest))
            await self._emit_ingested(repo_id, dest)
            return dest

        if dest.exists() and force_reclone:
            log.info("repo_reclone_forced", dest=str(dest))
            shutil.rmtree(dest, ignore_errors=True)

        return await self._clone_with_retry(
            url=url_or_path,
            dest=dest,
            repo_id=repo_id,
            progress_callback=progress_callback,
        )

    # ── Private ───────────────────────────────────────────────────────────────
    async def _open_local(self, path: Path, *, repo_id: str) -> Path:
        """Validate that a local directory is a Git repo and return its path."""
        try:
            git.Repo(path, search_parent_directories=False)
        except (git.InvalidGitRepositoryError, git.NoSuchPathError) as exc:
            raise InvalidRepositoryError(str(path)) from exc
        log.info("local_repo_opened", path=str(path))
        await self._emit_ingested(repo_id, path)
        return path

    def _destination_for(self, url: str) -> Path:
        """Derive a stable, unique cache directory for a given URL."""
        url_hash = hashlib.sha256(url.encode()).hexdigest()[:16]
        # Use the last path segment as a human-readable prefix
        slug = url.rstrip("/").split("/")[-1].replace(".git", "")
        return self._cache_dir / f"{slug}-{url_hash}"

    async def _clone_with_retry(
        self,
        url: str,
        dest: Path,
        repo_id: str,
        progress_callback: ProgressCallback | None,
    ) -> Path:
        """Attempt to clone with exponential back-off on transient failures."""
        dest.parent.mkdir(parents=True, exist_ok=True)
        last_error: Exception | None = None

        for attempt in range(1, _MAX_RETRY_ATTEMPTS + 1):
            try:
                log.info("clone_attempt", url=url, attempt=attempt, dest=str(dest))
                await self._do_clone(url, dest, progress_callback=progress_callback)
                log.info("clone_succeeded", url=url, dest=str(dest))
                await self._emit_ingested(repo_id, dest)
                return dest
            except CloneTimeoutError:
                # Timeout is non-retryable
                raise
            except RepositoryCloneError as exc:
                last_error = exc
                if attempt < _MAX_RETRY_ATTEMPTS:
                    delay = _RETRY_BASE_DELAY * (2 ** (attempt - 1))
                    log.warning(
                        "clone_failed_retrying",
                        url=url,
                        attempt=attempt,
                        delay=delay,
                        error=str(exc),
                    )
                    await asyncio.sleep(delay)
                else:
                    log.error("clone_failed_permanently", url=url, error=str(exc))

        raise last_error or RepositoryCloneError(url, "Unknown error after retries")

    async def _do_clone(
        self,
        url: str,
        dest: Path,
        progress_callback: ProgressCallback | None,
    ) -> None:
        """
        Run `git clone` in a thread pool and enforce the timeout.

        Raises:
            CloneTimeoutError: If the operation exceeds `self._timeout` seconds.
            RepositoryCloneError: If git reports an error.
        """
        loop = asyncio.get_running_loop()
        progress = _AsyncProgressBridge(loop, progress_callback) if progress_callback else None

        def _blocking_clone() -> None:
            try:
                git.Repo.clone_from(
                    url,
                    dest,
                    progress=progress,
                    depth=None,  # Full clone — required for git blame / churn analysis
                    multi_options=["--recurse-submodules=no"],
                )
            except git.GitCommandError as exc:
                # Clean up any partial clone
                if dest.exists():
                    shutil.rmtree(dest, ignore_errors=True)
                raise RepositoryCloneError(url, str(exc)) from exc

        start = time.monotonic()
        try:
            await asyncio.wait_for(
                asyncio.to_thread(_blocking_clone),
                timeout=float(self._timeout),
            )
        except TimeoutError:
            if dest.exists():
                shutil.rmtree(dest, ignore_errors=True)
            elapsed = int(time.monotonic() - start)
            raise CloneTimeoutError(url, elapsed) from None

    async def _emit_ingested(self, repo_id: str, path: Path) -> None:
        """Emit a RepositoryIngestedEvent on the event bus."""
        size = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
        await self._bus.emit(
            RepositoryIngestedEvent(
                repo_id=repo_id,
                local_path=path,
                size_bytes=size,
            )
        )
