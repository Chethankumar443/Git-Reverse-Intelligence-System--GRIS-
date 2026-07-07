"""
Async Event Bus for the Git Reverse analysis pipeline.

Architecture: Pub/Sub with typed events.
- Publishers (e.g., the Cloner, the AST Parser) emit events.
- Subscribers (e.g., Skill plugins, the Graph Builder) register handlers.
- The EventBus dispatches events concurrently to all matching subscribers.
- Subscriber failures are isolated: one failing handler does not cancel others.

Typical usage:
    bus = EventBus()

    @bus.on(RepositoryClonedEvent)
    async def handle_cloned(event: RepositoryClonedEvent) -> None:
        log.info("repo_cloned", path=str(event.local_path))

    await bus.emit(RepositoryClonedEvent(repo_id="abc", local_path=Path("/tmp/repo")))
"""

from __future__ import annotations

import asyncio
import inspect
from collections import defaultdict
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, TypeVar

from git_reverse.core.logging import get_logger

log = get_logger(__name__)

# ── Type Aliases ──────────────────────────────────────────────────────────────
AsyncHandler = Callable[..., Coroutine[Any, Any, None]]
EventT = TypeVar("EventT", bound="BaseEvent")


# ── Base Event ────────────────────────────────────────────────────────────────
@dataclass(frozen=True, slots=True)
class BaseEvent:
    """Root class for all pipeline events."""

    repo_id: str


# ── Pipeline Events ───────────────────────────────────────────────────────────
@dataclass(frozen=True, slots=True)
class RepositoryIngestedEvent(BaseEvent):
    """Fired after a repository has been cloned/located locally."""

    local_path: Path
    primary_language: str | None = None
    size_bytes: int = 0


@dataclass(frozen=True, slots=True)
class LanguageDetectedEvent(BaseEvent):
    """Fired when a specific language is identified in the repository."""

    language: str
    file_count: int
    percentage: float


@dataclass(frozen=True, slots=True)
class FrameworkDetectedEvent(BaseEvent):
    """Fired when a framework is confirmed in the repository."""

    framework: str
    evidence: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class ASTParseCompletedEvent(BaseEvent):
    """Fired after a single file's AST has been successfully parsed."""

    file_path: str
    language: str
    node_count: int


@dataclass(frozen=True, slots=True)
class ASTParseFailedEvent(BaseEvent):
    """Fired when AST parsing fails for a specific file (recoverable)."""

    file_path: str
    language: str
    reason: str


@dataclass(frozen=True, slots=True)
class GraphConstructedEvent(BaseEvent):
    """Fired when the complete knowledge graph has been assembled."""

    node_count: int
    edge_count: int


@dataclass(frozen=True, slots=True)
class AnalysisPipelineCompleteEvent(BaseEvent):
    """Fired when all analysis stages for a repository have finished."""

    duration_seconds: float


# ── The Event Bus ─────────────────────────────────────────────────────────────
class EventBus:
    """
    Async Pub/Sub event bus.

    Thread-safety: designed for use within a single asyncio event loop.
    Do not share an EventBus instance across threads.
    """

    def __init__(self) -> None:
        # Maps event class → list of async handlers
        self._handlers: defaultdict[type[BaseEvent], list[AsyncHandler]] = defaultdict(list)
        self._emit_count: int = 0
        self._error_count: int = 0

    def on(self, event_type: type[EventT]) -> Callable[[AsyncHandler], AsyncHandler]:
        """
        Decorator to register an async handler for a specific event type.

            @bus.on(LanguageDetectedEvent)
            async def handle(event: LanguageDetectedEvent) -> None: ...
        """

        def decorator(handler: AsyncHandler) -> AsyncHandler:
            if not inspect.iscoroutinefunction(handler):
                raise TypeError(
                    f"Event handler '{handler.__name__}' must be an async function."
                )
            self._handlers[event_type].append(handler)
            log.debug(
                "handler_registered",
                event_type=event_type.__name__,
                handler=handler.__name__,
            )
            return handler

        return decorator

    def subscribe(self, event_type: type[EventT], handler: AsyncHandler) -> None:
        """
        Register a handler programmatically (alternative to the decorator).

        Args:
            event_type: The event class to subscribe to.
            handler: An async callable accepting a single event argument.
        """
        if not inspect.iscoroutinefunction(handler):
            raise TypeError(
                f"Event handler '{handler.__name__}' must be an async function."
            )
        self._handlers[event_type].append(handler)

    def unsubscribe(self, event_type: type[EventT], handler: AsyncHandler) -> None:
        """Remove a previously registered handler."""
        try:
            self._handlers[event_type].remove(handler)
        except ValueError:
            pass  # Handler was not registered; ignore.

    async def emit(self, event: BaseEvent) -> int:
        """
        Dispatch an event to all registered handlers concurrently.

        Handler failures are caught individually — a single broken handler
        will not prevent others from running. Errors are logged at ERROR level.

        Args:
            event: The event instance to dispatch.

        Returns:
            The number of handlers that were invoked successfully.
        """
        event_type = type(event)
        handlers = self._handlers.get(event_type, [])

        if not handlers:
            log.debug("event_emitted_no_handlers", event_type=event_type.__name__)
            return 0

        self._emit_count += 1
        log.debug(
            "event_emitting",
            event_type=event_type.__name__,
            handler_count=len(handlers),
            repo_id=event.repo_id,
        )

        tasks = [asyncio.create_task(h(event), name=h.__name__) for h in handlers]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        success_count = 0
        for handler, result in zip(handlers, results, strict=True):
            if isinstance(result, BaseException):
                self._error_count += 1
                log.error(
                    "handler_failed",
                    event_type=event_type.__name__,
                    handler=handler.__name__,
                    error=str(result),
                    exc_info=result,
                )
            else:
                success_count += 1

        return success_count

    def clear(self) -> None:
        """Deregister all handlers. Useful in tests."""
        self._handlers.clear()

    @property
    def stats(self) -> dict[str, int]:
        """Return basic diagnostic statistics."""
        return {
            "total_events_emitted": self._emit_count,
            "total_handler_errors": self._error_count,
            "registered_event_types": len(self._handlers),
        }


# ── Singleton for the application ─────────────────────────────────────────────
_bus: EventBus | None = None


def get_event_bus() -> EventBus:
    """Return the global application EventBus singleton."""
    global _bus
    if _bus is None:
        _bus = EventBus()
    return _bus


def reset_event_bus() -> None:
    """Reset the singleton. Call this in tests to get a clean bus."""
    global _bus
    _bus = None
