"""Tests for TUI Settings Screen."""

from __future__ import annotations

import pytest
from textual.app import App

from git_reverse.config.settings import AppSettings
from git_reverse.tui.settings import SettingsScreen
from textual.widgets import Button


@pytest.mark.asyncio
async def test_settings_screen_loads(settings: AppSettings) -> None:
    """Verify that SettingsScreen can mount and displays initial values."""
    class TestApp(App[None]):
        def compose(self):
            # yield settings screen on start for testing
            yield Button("Open", id="open-btn")

    app = TestApp()
    async with app.run_test() as pilot:
        screen = SettingsScreen(settings)
        await app.push_screen(screen)
        
        # Verify inputs populated
        from textual.widgets import Input
        model_input = screen.query_one("#default-model", Input)
        assert model_input.value == settings.default_model

        workers_input = screen.query_one("#analysis-workers", Input)
        assert workers_input.value == str(settings.analysis_workers)
        
        # Dismiss
        await screen.dismiss()
