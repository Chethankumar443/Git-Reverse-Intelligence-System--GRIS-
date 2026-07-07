"""
TUI Onboarding Setup Flow.

Prompts for username and OpenRouter API key on initial install,
validates the key, lists free-tier models, and saves choices.
"""

from __future__ import annotations

import httpx
from textual import on, work
from textual.app import ComposeResult
from textual.containers import Container, Grid
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, ListItem, ListView

from git_reverse.config.settings import AppSettings


class OnboardingListItem(ListItem):
    """ListItem representing a model with type-safe attributes."""
    model_id: str


class OnboardingScreen(ModalScreen[None]):
    """Onboarding setup wizard for new users."""

    def __init__(self, settings: AppSettings) -> None:
        super().__init__()
        self._settings = settings
        self._free_models: list[tuple[str, str]] = []
        self._selected_model_id: str | None = None

    def compose(self) -> ComposeResult:
        with Container(id="onboarding-container"):
            yield Label("Welcome to Git Reverse Setup", id="onboarding-title")

            with Grid(id="onboarding-grid"):
                yield Label("Set Username:")
                yield Input(placeholder="e.g. cheth", id="ob-username")

                yield Label("OpenRouter API Key:\nGet key at openrouter.ai/keys")
                yield Input(placeholder="sk-or-v1-...", password=True, id="ob-api-key")

            yield Button("Validate Key & Fetch Free Models", id="validate-btn", variant="primary")

            yield Label("Select Default Model:", id="model-label")
            with Container(id="model-selection-box"):
                yield ListView(id="ob-model-list")

            yield Label("", id="onboarding-status")

            with Container(id="buttons-row"):
                yield Button("Save & Complete", id="complete-btn", variant="success", disabled=True)

    @on(Button.Pressed, "#validate-btn")
    def on_validate(self) -> None:
        """Trigger API key validation worker."""
        key = self.query_one("#ob-api-key", Input).value.strip()
        if not key:
            self.query_one("#onboarding-status", Label).update("❌ API key cannot be empty.")
            return

        self.query_one("#onboarding-status", Label).update("⏳ Validating and fetching models...")
        self.query_one("#validate-btn", Button).disabled = True
        self._validate_and_fetch(key)

    @work
    async def _validate_and_fetch(self, api_key: str) -> None:
        """Asynchronously call OpenRouter API to fetch and filter free-tier models."""
        url = "https://openrouter.ai/api/v1/models"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": "https://github.com/Chethankumar443/Git-Reverse-CLI",
            "X-Title": "Git Reverse",
        }
        try:
            async with httpx.AsyncClient() as client:
                res = await client.get(url, headers=headers, timeout=12.0)

            if res.status_code != 200:
                self._update_status(f"❌ Validation failed (HTTP {res.status_code})")
                return

            data = res.json()
            models = data.get("data", [])
            free_list = []
            for m in models:
                pricing = m.get("pricing", {})
                prompt_cost = float(pricing.get("prompt") or 0.0)
                completion_cost = float(pricing.get("completion") or 0.0)
                if prompt_cost == 0.0 and completion_cost == 0.0:
                    free_list.append((m.get("id"), m.get("name") or m.get("id")))

            if not free_list:
                self._update_status("⚠️ Key is valid, but no free-tier models found.")
                return

            self._free_models = free_list
            self._update_model_list()
            self._update_status("✅ Key validated! Select a free model below to finish.")

        except Exception as exc:
            self._update_status(f"❌ Network connection failed: {exc}")
        finally:
            self._enable_validate_btn()

    def _update_status(self, text: str) -> None:
        self.query_one("#onboarding-status", Label).update(text)

    def _enable_validate_btn(self) -> None:
        self.query_one("#validate-btn", Button).disabled = False

    def _update_model_list(self) -> None:
        def update_ui() -> None:
            list_view = self.query_one("#ob-model-list", ListView)
            list_view.clear()
            for model_id, model_name in self._free_models:
                item = OnboardingListItem(Label(model_name))
                item.model_id = model_id
                list_view.append(item)

            # Enable complete button if we have models populated
            self.query_one("#complete-btn", Button).disabled = False

        update_ui()

    @on(ListView.Selected, "#ob-model-list")
    def on_model_selected(self, event: ListView.Selected) -> None:
        if isinstance(event.item, OnboardingListItem):
            self._selected_model_id = event.item.model_id

    @on(Button.Pressed, "#complete-btn")
    def on_complete(self) -> None:
        """Save settings and dismiss onboarding."""
        username = self.query_one("#ob-username", Input).value.strip()
        api_key = self.query_one("#ob-api-key", Input).value.strip()

        if not username:
            self.query_one("#onboarding-status", Label).update("❌ Username cannot be empty.")
            return

        if not self._selected_model_id:
            # Default fallback if they didn't explicitly click one
            if self._free_models:
                self._selected_model_id = self._free_models[0][0]
            else:
                self._selected_model_id = "google/gemini-flash-1.5"

        # Save credentials to OS Keychain
        self._settings.save_openrouter_key(api_key)

        # Save settings
        self._settings.username = username
        self._settings.default_model = self._selected_model_id
        self._settings.save_settings()

        self.dismiss()
