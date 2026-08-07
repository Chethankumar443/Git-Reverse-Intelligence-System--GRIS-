from textual.widget import Widget
from textual.widgets import Static, ProgressBar
from textual.app import ComposeResult
from textual import on
from rich.markup import escape

class AnalysisProgressPanel(Widget):
    """Multi-stage progress display for active analysis tasks."""

    DEFAULT_CSS = """
    AnalysisProgressPanel {
        height: auto;
        padding: 0 1;
    }
    AnalysisProgressPanel .stage-label {
        color: #8b949e;
    }
    AnalysisProgressPanel .stage-active {
        color: #58a6ff;
    }
    AnalysisProgressPanel .stage-complete {
        color: #2ea043;
    }
    """

    STAGE_LABELS = {
        "clone": "  Cloning",
        "scan": "  Scanning",
        "parse": "  Parsing AST",
        "analyze": "  Analyzing",
        "complete": "  Complete",
        "error": "  Error",
    }

    def __init__(self, url: str, **kwargs):
        super().__init__(**kwargs)
        self.url = url
        self._stage = "clone"
        self._message = "Waiting..."
        self._percent = 0.0

    def compose(self) -> ComposeResult:
        yield Static(f"[bold]{escape(self.url)}[/bold]", id="url-label")
        yield Static(self._message, id="stage-msg")
        yield ProgressBar(total=100, show_eta=False, id="progress")

    def update_progress(self, stage: str, message: str, percent: float) -> None:
        self._stage = stage
        self._message = message
        self._percent = percent

        stage_label = self.STAGE_LABELS.get(stage, stage)

        if stage == "error":
            color = "red"
        elif stage == "complete":
            color = "green"
        else:
            color = "cyan"

        label = f"[{color}]{stage_label}[/{color}]  {escape(message)}"
        self.query_one("#stage-msg", Static).update(label)
        self.query_one("#progress", ProgressBar).progress = percent
