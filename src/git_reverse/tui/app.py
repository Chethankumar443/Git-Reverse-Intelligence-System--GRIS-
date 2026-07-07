"""
Git Reverse TUI Application.

Built with Textual for a Warp/Linear-inspired terminal experience.
Design priorities:
  - Keyboard-first: every action is reachable without a mouse.
  - Non-blocking: all analysis and LLM calls run in async workers.
  - Information-dense: maximum data, minimal chrome.
  - Streaming: markdown renders progressively as the LLM responds.

Layout (Phase 1 — scaffold):
  ┌─ Header ──────────────────────────────────────────────┐
  │  Git Reverse  │  Session ID  │  Mode  │  Model        │
  ├─ Sidebar ─────┤─ Main Panel ──────────────────────────┤
  │ Session list  │                                       │
  │ Repository    │  Welcome / Dashboard                  │
  │ tree          │                                       │
  │               │                                       │
  ├───────────────┴───────────────────────────────────────┤
  │  Status bar: repo | branch | workers | key status     │
  └───────────────────────────────────────────────────────┘

Subsequent phases will fill the main panel with the analysis
dashboard, streaming chat pane, and graph visualizer.
"""

from __future__ import annotations

from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.reactive import reactive
from textual.screen import Screen
from textual.widgets import (
    Footer,
    Header,
    Input,
    Label,
    ListItem,
    ListView,
    Markdown,
    Static,
)

from git_reverse.config.settings import AppSettings
from git_reverse.core.logging import get_logger
from git_reverse.storage.database import Database, Session, SessionDAO

log = get_logger(__name__)

# ── CSS (Textual CSS) ─────────────────────────────────────────────────────────
# Defined inline to keep Phase 1 self-contained. Phase 3 will move this to a
# dedicated .tcss file alongside theme support.
_APP_CSS = """
Screen {
    background: $surface;
}

#sidebar {
    width: 28;
    min-width: 20;
    border-right: solid $primary-darken-2;
    padding: 0 1;
    overflow-y: auto;
}

#sidebar-title {
    color: $primary;
    text-style: bold;
    padding: 1 0 0 0;
    border-bottom: solid $primary-darken-3;
    margin-bottom: 1;
}

#main-panel {
    padding: 1 2;
    overflow-y: auto;
}

#welcome-heading {
    color: $accent;
    text-style: bold;
    padding-bottom: 1;
}

#repo-input-container {
    margin-top: 2;
    border: solid $primary-darken-2;
    padding: 1;
}

#repo-input-label {
    color: $text-muted;
    margin-bottom: 1;
}

Input {
    border: solid $primary-darken-1;
}

Input:focus {
    border: solid $accent;
}

#session-list-title {
    color: $text-muted;
    text-style: italic;
    padding: 0 0 1 0;
}

.session-item {
    padding: 0 1;
}

.session-item:hover {
    background: $primary-darken-2;
}

#status-bar {
    height: 1;
    background: $primary-darken-3;
    padding: 0 1;
    color: $text-muted;
}
"""

_WELCOME_TEXT = """\
# Git Reverse

**Repository Intelligence Platform**

Transform any Git repository into structured knowledge: AST graphs,
dependency maps, architecture diagrams, and LLM-powered interactive analysis.

---

### Getting Started

1. Paste a GitHub URL or local path in the input below and press **Enter**.
2. Git Reverse will clone, validate, and begin the analysis pipeline.
3. Ask questions, generate blueprints, and explore the codebase interactively.

---

### Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Ctrl+P` | Command palette |
| `Ctrl+N` | New session |
| `Ctrl+R` | Resume last session |
| `Ctrl+S` | Save session |
| `Ctrl+M` | Switch model |
| `Ctrl+T` | Toggle theme |
| `Tab` | Cycle focus |
| `Esc` | Close / cancel |
| `?` | Help |

---

> **Local First.** Nothing leaves your machine. All sessions, analysis,
> and embeddings are stored in `~/.local/share/git-reverse/`.
"""


# ── Sidebar ───────────────────────────────────────────────────────────────────
class Sidebar(Vertical):
    """Left panel: session list and repository tree."""

    DEFAULT_CSS = ""

    def compose(self) -> ComposeResult:
        yield Label("◈ Git Reverse", id="sidebar-title")
        yield Label("Recent Sessions", id="session-list-title")
        yield ListView(id="session-list")

    def populate_sessions(self, sessions: list[Session]) -> None:
        """Render session list items from database records."""
        session_list = self.query_one("#session-list", ListView)
        session_list.clear()
        if not sessions:
            session_list.append(ListItem(Label("No sessions yet.", classes="session-item")))
            return
        for session in sessions:
            label = f"{session.id}  [{session.mode}]"
            session_list.append(ListItem(Label(label, classes="session-item")))


# ── Main Panel ────────────────────────────────────────────────────────────────
class MainPanel(Vertical):
    """Right panel: dashboard, analysis view, and chat interface."""

    def compose(self) -> ComposeResult:
        yield Markdown(_WELCOME_TEXT, id="welcome-content")
        with Container(id="repo-input-container"):
            yield Label("Enter a GitHub URL or local path to begin:", id="repo-input-label")
            yield Input(
                placeholder="https://github.com/owner/repo  or  /path/to/local/repo",
                id="repo-input",
            )


# ── Status Bar ────────────────────────────────────────────────────────────────
class StatusBar(Static):
    """One-line status bar showing active context."""

    repo_name: reactive[str] = reactive("No repository")
    model_name: reactive[str] = reactive("—")
    session_id: reactive[str] = reactive("—")

    def render(self) -> str:
        return (
            f" ◈ {self.repo_name}  │  Model: {self.model_name}  "
            f"│  Session: {self.session_id} "
        )


# ── The Application ───────────────────────────────────────────────────────────
class GitReverseApp(App[None]):
    """
    The root Textual application for Git Reverse.

    Manages the top-level layout and global keybindings. Business logic
    is delegated to async workers to keep the event loop responsive.
    """

    CSS = _APP_CSS
    TITLE = "Git Reverse"
    SUB_TITLE = "Repository Intelligence Platform"

    BINDINGS = [
        Binding("ctrl+p", "command_palette", "Command Palette", priority=True),
        Binding("ctrl+n", "new_session", "New Session"),
        Binding("ctrl+r", "resume_session", "Resume Session"),
        Binding("ctrl+s", "save_session", "Save"),
        Binding("ctrl+m", "switch_model", "Model"),
        Binding("ctrl+t", "toggle_theme", "Theme"),
        Binding("ctrl+q", "quit", "Quit", priority=True),
        Binding("question_mark", "show_help", "Help", key_display="?"),
    ]

    def __init__(self, settings: AppSettings, db: Database) -> None:
        super().__init__()
        self._settings = settings
        self._db = db
        self._session_dao = SessionDAO(db)

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="body"):
            yield Sidebar(id="sidebar")
            yield MainPanel(id="main-panel")
        yield StatusBar(id="status-bar")
        yield Footer()

    def on_mount(self) -> None:
        """Load initial data after the DOM is ready."""
        self._load_recent_sessions()

    @work(exclusive=True)
    async def _load_recent_sessions(self) -> None:
        """Fetch recent sessions from SQLite and populate the sidebar."""
        try:
            sessions = await self._session_dao.list_recent(limit=15)
            self.query_one(Sidebar).populate_sessions(sessions)
        except Exception as exc:  # noqa: BLE001
            log.error("failed_to_load_sessions", error=str(exc))

    @on(Input.Submitted, "#repo-input")
    async def on_repo_submitted(self, event: Input.Submitted) -> None:
        """Handle repository URL/path submission from the main input."""
        url = event.value.strip()
        if not url:
            return
        event.input.clear()
        log.info("repo_input_received", url=url)
        # Phase 2 will wire this to the analysis pipeline.
        # For now, show feedback.
        self.notify(f"Analysis queued: {url}", title="Git Reverse", severity="information")

    # ── Actions ───────────────────────────────────────────────────────────────
    async def action_new_session(self) -> None:
        """Create a new blank session."""
        session = await self._session_dao.create(
            model=self._settings.default_model,
            mode="explore",
            username=self._settings.username or None,
        )
        status = self.query_one(StatusBar)
        status.session_id = session.id
        self._load_recent_sessions()
        self.notify(f"Session {session.id} started.", severity="information")

    async def action_toggle_theme(self) -> None:
        """Toggle between dark and light themes."""
        self.dark = not self.dark

    async def action_command_palette(self) -> None:
        """Show the command palette (Phase 3)."""
        self.notify("Command palette coming in Phase 3.", severity="warning")

    async def action_switch_model(self) -> None:
        """Open model selection screen (Phase 4)."""
        self.notify("Model switcher coming in Phase 4.", severity="warning")

    async def action_resume_session(self) -> None:
        """Resume the most recent session."""
        self.notify("Session resume coming in Phase 3.", severity="warning")

    async def action_save_session(self) -> None:
        """Save the current session state."""
        self.notify("Session saved.", severity="success")

    async def action_show_help(self) -> None:
        """Display the help overlay (Phase 3)."""
        self.notify("Press Ctrl+P to open the command palette.", severity="information")
