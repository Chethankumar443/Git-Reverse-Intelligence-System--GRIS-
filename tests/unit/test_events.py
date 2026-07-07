"""
Tests for the async EventBus — registration, dispatch, concurrency,
failure isolation, and singleton management.
"""

from __future__ import annotations

import asyncio

import pytest

from git_reverse.core.events import (
    BaseEvent,
    EventBus,
    LanguageDetectedEvent,
    RepositoryIngestedEvent,
    get_event_bus,
    reset_event_bus,
)
from pathlib import Path


class TestEventBus:
    """Unit tests for EventBus Pub/Sub mechanics."""

    async def test_emit_with_no_handlers_returns_zero(self, event_bus: EventBus) -> None:
        count = await event_bus.emit(
            RepositoryIngestedEvent(repo_id="r1", local_path=Path("."), size_bytes=0)
        )
        assert count == 0

    async def test_single_handler_invoked(self, event_bus: EventBus) -> None:
        received: list[str] = []

        @event_bus.on(RepositoryIngestedEvent)
        async def handle(event: RepositoryIngestedEvent) -> None:
            received.append(event.repo_id)

        await event_bus.emit(
            RepositoryIngestedEvent(repo_id="r1", local_path=Path("."), size_bytes=0)
        )
        assert received == ["r1"]

    async def test_multiple_handlers_all_invoked(self, event_bus: EventBus) -> None:
        calls: list[int] = []

        @event_bus.on(RepositoryIngestedEvent)
        async def h1(event: RepositoryIngestedEvent) -> None:
            calls.append(1)

        @event_bus.on(RepositoryIngestedEvent)
        async def h2(event: RepositoryIngestedEvent) -> None:
            calls.append(2)

        count = await event_bus.emit(
            RepositoryIngestedEvent(repo_id="r1", local_path=Path("."), size_bytes=0)
        )
        assert count == 2
        assert sorted(calls) == [1, 2]

    async def test_handler_failure_does_not_cancel_others(self, event_bus: EventBus) -> None:
        """A failing handler must not prevent remaining handlers from running."""
        results: list[str] = []

        @event_bus.on(RepositoryIngestedEvent)
        async def bad_handler(event: RepositoryIngestedEvent) -> None:
            raise RuntimeError("simulated failure")

        @event_bus.on(RepositoryIngestedEvent)
        async def good_handler(event: RepositoryIngestedEvent) -> None:
            results.append("ok")

        await event_bus.emit(
            RepositoryIngestedEvent(repo_id="r1", local_path=Path("."), size_bytes=0)
        )
        assert results == ["ok"]
        assert event_bus.stats["total_handler_errors"] == 1

    async def test_different_event_types_do_not_cross_trigger(
        self, event_bus: EventBus
    ) -> None:
        ingested_calls: list[str] = []
        language_calls: list[str] = []

        @event_bus.on(RepositoryIngestedEvent)
        async def on_ingested(event: RepositoryIngestedEvent) -> None:
            ingested_calls.append("ingested")

        @event_bus.on(LanguageDetectedEvent)
        async def on_language(event: LanguageDetectedEvent) -> None:
            language_calls.append("language")

        await event_bus.emit(
            RepositoryIngestedEvent(repo_id="r1", local_path=Path("."), size_bytes=0)
        )
        assert ingested_calls == ["ingested"]
        assert language_calls == []

    async def test_subscribe_programmatic_api(self, event_bus: EventBus) -> None:
        calls: list[str] = []

        async def handler(event: RepositoryIngestedEvent) -> None:
            calls.append(event.repo_id)

        event_bus.subscribe(RepositoryIngestedEvent, handler)
        await event_bus.emit(
            RepositoryIngestedEvent(repo_id="prog-001", local_path=Path("."), size_bytes=0)
        )
        assert calls == ["prog-001"]

    async def test_unsubscribe_removes_handler(self, event_bus: EventBus) -> None:
        calls: list[str] = []

        async def handler(event: RepositoryIngestedEvent) -> None:
            calls.append(event.repo_id)

        event_bus.subscribe(RepositoryIngestedEvent, handler)
        event_bus.unsubscribe(RepositoryIngestedEvent, handler)
        await event_bus.emit(
            RepositoryIngestedEvent(repo_id="r1", local_path=Path("."), size_bytes=0)
        )
        assert calls == []

    def test_registering_sync_handler_raises(self, event_bus: EventBus) -> None:
        def sync_handler(event: RepositoryIngestedEvent) -> None:
            pass

        with pytest.raises(TypeError, match="async"):
            event_bus.subscribe(RepositoryIngestedEvent, sync_handler)  # type: ignore

    async def test_stats_track_emissions_and_errors(self, event_bus: EventBus) -> None:
        @event_bus.on(RepositoryIngestedEvent)
        async def bad(event: RepositoryIngestedEvent) -> None:
            raise ValueError

        await event_bus.emit(
            RepositoryIngestedEvent(repo_id="s1", local_path=Path("."), size_bytes=0)
        )
        await event_bus.emit(
            RepositoryIngestedEvent(repo_id="s2", local_path=Path("."), size_bytes=0)
        )
        stats = event_bus.stats
        assert stats["total_events_emitted"] == 2
        assert stats["total_handler_errors"] == 2

    async def test_clear_removes_all_handlers(self, event_bus: EventBus) -> None:
        calls: list[str] = []

        @event_bus.on(RepositoryIngestedEvent)
        async def handler(event: RepositoryIngestedEvent) -> None:
            calls.append("x")

        event_bus.clear()
        await event_bus.emit(
            RepositoryIngestedEvent(repo_id="r1", local_path=Path("."), size_bytes=0)
        )
        assert calls == []


class TestEventBusSingleton:
    def test_get_event_bus_returns_singleton(self) -> None:
        reset_event_bus()
        bus1 = get_event_bus()
        bus2 = get_event_bus()
        assert bus1 is bus2

    def test_reset_creates_new_instance(self) -> None:
        reset_event_bus()
        bus1 = get_event_bus()
        reset_event_bus()
        bus2 = get_event_bus()
        assert bus1 is not bus2
