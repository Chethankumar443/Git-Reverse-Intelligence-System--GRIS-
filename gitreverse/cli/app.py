import asyncio
from typing import AsyncIterator

from textual.app import App, ComposeResult
from textual.widgets import (
    Header,
    Footer,
    Input,
    Button,
    Label,
    TabbedContent,
    TabPane,
)
from textual.containers import Vertical, Horizontal, ScrollableContainer
from textual.reactive import reactive
from rich.markup import escape

from gitreverse.core.pipeline import AnalysisPipeline, PipelineProgress
from gitreverse.storage.database import DatabaseManager
from gitreverse.cli.views.progress import AnalysisProgressPanel
from gitreverse.cli.views.results import ResultsPanel
from gitreverse.utils.logging import setup_logging, get_logger

logger = get_logger("cli.app")


class GitReverseApp(App):
    """Git Reverse — Repository Intelligence Platform TUI."""

    TITLE = "Git Reverse"
    SUB_TITLE = "Repository Intelligence Platform"

    CSS = """
    /* ── Layout ── */
    Screen {
        background: $surface;
    }

    #app-body {
        height: 1fr;
        padding: 0 1;
    }

    #input-row {
        height: 3;
        align: left middle;
    }

    #url-input {
        width: 1fr;
        margin-right: 1;
    }

    #analyze-btn {
        width: 16;
        background: $accent;
    }

    #progress-section {
        height: auto;
        max-height: 40%;
        border: round $surface-lighten-1;
        padding: 0 1;
    }

    #progress-label {
        color: $text-muted;
        padding-bottom: 1;
    }

    ResultsPanel {
        height: 1fr;
        margin-top: 1;
    }

    #status-bar {
        height: 1;
        background: $surface-darken-1;
        color: $text-muted;
        padding: 0 2;
    }
    """

    BINDINGS = [
        ("ctrl+q", "quit", "Quit"),
        ("ctrl+k", "focus_input", "Focus URL input"),
        ("escape", "cancel_analysis", "Cancel"),
    ]

    model_name: reactive[str] = reactive("OpenRouter")
    active_repo: reactive[str] = reactive("No repository loaded")
    mode: reactive[str] = reactive("IDLE")

    def __init__(self):
        super().__init__()
        self.db = DatabaseManager()
        self.pipeline = AnalysisPipeline(db=self.db)
        self._active_tasks: dict[str, asyncio.Task] = {}

    # ── Compose ──────────────────────────────────────────────────────────────

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        with Vertical(id="app-body"):
            with Horizontal(id="input-row"):
                yield Input(
                    placeholder="Paste GitHub URL… (e.g. https://github.com/expressjs/express)",
                    id="url-input",
                )
                yield Button("⚡ Analyze", id="analyze-btn", variant="primary")

            yield Label(" Active Analyses", id="progress-label")
            with ScrollableContainer(id="progress-section"):
                pass  # Progress panels injected dynamically

            yield ResultsPanel(id="results-panel")

        yield Label(self._status_text(), id="status-bar")
        yield Footer()

    # ── Status bar ──────────────────────────────────────────────────────────

    def _status_text(self) -> str:
        return (
            f" [{self.mode}]  "
            f"Model: {self.model_name}  │  "
            f"Repo: {self.active_repo}  │  "
            f"Ctrl+K: focus  Ctrl+Q: quit  Esc: cancel"
        )

    def watch_mode(self, value: str) -> None:
        self._update_status_bar()

    def watch_active_repo(self, value: str) -> None:
        self._update_status_bar()

    def _update_status_bar(self) -> None:
        try:
            self.query_one("#status-bar", Label).update(self._status_text())
        except Exception:
            pass

    # ── Actions ─────────────────────────────────────────────────────────────

    def action_focus_input(self) -> None:
        self.query_one("#url-input", Input).focus()

    async def action_cancel_analysis(self) -> None:
        for url, task in list(self._active_tasks.items()):
            if not task.done():
                task.cancel()
                logger.info(f"Cancelled analysis task for {url}")
        self.mode = "IDLE"

    # ── Event Handlers ───────────────────────────────────────────────────────

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "analyze-btn":
            await self._start_analysis()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "url-input":
            await self._start_analysis()

    # ── Pipeline ─────────────────────────────────────────────────────────────

    async def _start_analysis(self) -> None:
        url = self.query_one("#url-input", Input).value.strip()
        if not url:
            return

        if url in self._active_tasks and not self._active_tasks[url].done():
            self._show_result(f"⚠️ Already analyzing `{url}`")
            return

        # Inject progress panel
        panel = AnalysisProgressPanel(url=url, id=f"progress-{hash(url)}")
        await self.query_one("#progress-section").mount(panel)

        self.active_repo = url.split("/")[-1]
        self.mode = "ANALYZING"

        task = asyncio.create_task(self._run_pipeline(url, panel))
        self._active_tasks[url] = task

        # Clear input
        self.query_one("#url-input", Input).value = ""

    async def _run_pipeline(self, url: str, panel: AnalysisProgressPanel) -> None:
        try:
            async for progress in self.pipeline.run(url):
                panel.update_progress(progress.stage, progress.message, progress.percent)

                if progress.stage == "complete":
                    self.mode = "READY"
                    self._show_result(
                        f"## ✅ Analysis Complete\n\n"
                        f"**Repository**: `{url}`\n\n"
                        f"{escape(progress.message)}\n\n"
                        f"Ask a question about this repository in the input field."
                    )
                elif progress.stage == "error":
                    self.mode = "ERROR"
                    self._show_result(f"## ❌ Analysis Failed\n\n{escape(progress.message)}")

        except asyncio.CancelledError:
            panel.update_progress("error", "Analysis cancelled by user.", 0.0)
            self.mode = "IDLE"
        except Exception as e:
            logger.error(f"Pipeline error for {url}: {e}")
            panel.update_progress("error", str(e), 0.0)
            self.mode = "ERROR"
        finally:
            self._active_tasks.pop(url, None)

    def _show_result(self, markdown: str) -> None:
        try:
            self.query_one("#results-panel", ResultsPanel).set_content(markdown)
        except Exception:
            pass


def main() -> None:
    setup_logging()
    app = GitReverseApp()
    app.run()


if __name__ == "__main__":
    main()
