from textual.widget import Widget
from textual.widgets import Static, Markdown
from textual.app import ComposeResult
from textual.scroll_view import ScrollView

class ResultsPanel(Widget):
    """Scrollable results area with streaming markdown support."""

    DEFAULT_CSS = """
    ResultsPanel {
        height: 1fr;
        border: round $surface-lighten-1;
        padding: 0 1;
    }
    ResultsPanel .results-header {
        color: $text-muted;
        padding-bottom: 1;
        border-bottom: solid $surface-lighten-1;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static(" Results", classes="results-header")
        yield Markdown("", id="results-md")

    def set_content(self, markdown_text: str) -> None:
        self.query_one("#results-md", Markdown).update(markdown_text)

    def append_content(self, markdown_text: str) -> None:
        existing = self.query_one("#results-md", Markdown)
        existing.update(getattr(existing, "_markdown", "") + "\n" + markdown_text)
