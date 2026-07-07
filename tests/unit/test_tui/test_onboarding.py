"""Tests for TUI Onboarding Screen."""

from __future__ import annotations

import pytest
from textual.app import App
from textual.widgets import Button, Input

from git_reverse.config.settings import AppSettings
from git_reverse.tui.onboarding import OnboardingScreen


@pytest.mark.asyncio
async def test_onboarding_screen_mounts(settings: AppSettings) -> None:
    """Verify that OnboardingScreen can mount and exposes inputs."""
    class TestApp(App[None]):
        def compose(self):
            yield Button("Start", id="start-btn")

    app = TestApp()
    async with app.run_test() as pilot:
        screen = OnboardingScreen(settings)
        await app.push_screen(screen)
        
        username_input = screen.query_one("#ob-username", Input)
        assert username_input.value == ""

        api_key_input = screen.query_one("#ob-api-key", Input)
        assert api_key_input.value == ""
        
        # Clean dismissal
        await screen.dismiss()
