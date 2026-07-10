"""
TUI Settings Screen.

Modal screen for managing application configuration and credential keyrings.
"""

from __future__ import annotations

from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Grid
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label

from git_reverse.config.settings import AppSettings


class SettingsScreen(ModalScreen[None]):
    """Modal dialog screen for updating application settings."""

    def __init__(self, settings: AppSettings) -> None:
        super().__init__()
        self._settings = settings

    def compose(self) -> ComposeResult:
        with Container(id="settings-container"):
            yield Label("Configuration Settings", id="settings-title")

            with Grid(id="settings-grid"):
                yield Label("Username:")
                yield Input(value=self._settings.username, id="settings-username")

                yield Label("Default Model:")
                yield Input(value=self._settings.default_model, id="default-model")

                yield Label("Analysis Workers:")
                yield Input(value=str(self._settings.analysis_workers), id="analysis-workers")

                yield Label("OpenRouter API Key:")
                yield Input(
                    value=self._settings.get_openrouter_key() or "",
                    password=True,
                    id="openrouter-key",
                )

                yield Label("GitHub API Token:")
                yield Input(
                    value=self._settings.get_github_token() or "",
                    password=True,
                    id="github-token",
                )

            yield Label("", id="settings-status")

            with Container(id="buttons-row"):
                yield Button("Cancel", id="cancel-btn", variant="error")
                yield Button("Save", id="save-btn", variant="success")

    @on(Button.Pressed, "#cancel-btn")
    def on_cancel(self) -> None:
        self.dismiss()

    @on(Button.Pressed, "#save-btn")
    def on_save(self) -> None:
        """Save settings updates and keyring secrets."""
        username = self.query_one("#settings-username", Input).value.strip()
        model = self.query_one("#default-model", Input).value.strip()
        workers_str = self.query_one("#analysis-workers", Input).value.strip()
        or_key = self.query_one("#openrouter-key", Input).value.strip()
        gh_token = self.query_one("#github-token", Input).value.strip()

        if not username:
            self.query_one("#settings-status", Label).update("[red]Username cannot be empty.[/]")
            return

        try:
            workers = int(workers_str) if workers_str else 2
        except ValueError:
            workers = 2

        # 1. Update config settings
        self._settings.username = username
        self._settings.default_model = model
        self._settings.analysis_workers = workers

        # 2. Save credentials to secure OS Keychain via Settings helper
        if or_key:
            self._settings.save_openrouter_key(or_key)
        if gh_token:
            self._settings.save_github_token(gh_token)

        # 3. Persist updated configuration permanently
        self._settings.save_settings()

        if hasattr(self.app, "set_status_message"):
            self.app.set_status_message("Settings updated successfully.")
        self.dismiss()
