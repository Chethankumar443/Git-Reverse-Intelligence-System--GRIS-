"""
TUI Command Palette.

Modal screen for quick command operations and fuzzy command searches.
"""

from __future__ import annotations

from textual import on
from textual.app import ComposeResult
from textual.containers import Container
from textual.screen import ModalScreen
from textual.widgets import Input, Label, ListItem, ListView

_COMMANDS = [
    ("settings", "Open Configuration Settings Screen"),
    ("theme", "Toggle Light / Dark UI Theme"),
    ("new_session", "Start a New Exploration Session"),
    ("resume", "Resume the Last active Session"),
    ("help", "Show help and keyboard shortcuts"),
    ("quit", "Exit Git Reverse"),
]


class CommandPalette(ModalScreen[str]):
    """Modal screen offering command searches and quick triggers."""

    DEFAULT_CSS = """
CommandPalette {
    align: center top;
    padding-top: 4;
}

#palette-container {
    width: 60;
    max-height: 24;
    border: solid $primary;
    background: $surface;
}

#palette-input {
    border: none;
    margin: 0;
    background: $surface;
}

ListView {
    background: $surface;
    overflow-y: auto;
}

.palette-item {
    padding: 0 1;
}

.palette-name {
    color: $accent;
    text-style: bold;
}

.palette-desc {
    color: $text-muted;
    margin-left: 2;
}
"""

    def compose(self) -> ComposeResult:
        with Container(id="palette-container"):
            yield Input(placeholder="Type a command...", id="palette-input")
            yield ListView(id="palette-list")

    def on_mount(self) -> None:
        self.query_one("#palette-input", Input).focus()
        self._populate_list("")

    def _populate_list(self, filter_text: str) -> None:
        list_view = self.query_one("#palette-list", ListView)
        list_view.clear()
        
        normalized = filter_text.strip().lower()
        for cmd, desc in _COMMANDS:
            if not normalized or normalized in cmd or normalized in desc.lower():
                label = f"{cmd:<12} {desc}"
                item = ListItem(Label(label, classes="palette-item"))
                item.name = cmd
                list_view.append(item)

    @on(Input.Changed, "#palette-input")
    def on_input_changed(self, event: Input.Changed) -> None:
        self._populate_list(event.value)

    @on(Input.Submitted, "#palette-input")
    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Trigger command on submission."""
        list_view = self.query_one("#palette-list", ListView)
        if list_view.children:
            selected_item = list_view.highlighted_child
            if selected_item:
                cmd_name = getattr(selected_item, "name", None)
                if cmd_name:
                    self.dismiss(cmd_name)
                    return
        self.dismiss("")

    @on(ListView.Selected, "#palette-list")
    def on_list_selected(self, event: ListView.Selected) -> None:
        cmd_name = getattr(event.item, "name", None)
        if cmd_name:
            self.dismiss(cmd_name)
