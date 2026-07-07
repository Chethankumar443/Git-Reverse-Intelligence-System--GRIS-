"""
Git Reverse TUI Application.

Handles the keyboard-driven workspace interaction, async cloning and parsing,
and displays the sidebar session list and chat interactions.
"""

from __future__ import annotations

import uuid
from pathlib import Path

from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.reactive import reactive
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

from git_reverse.analysis.pipeline import AnalysisPipeline
from git_reverse.config.settings import AppSettings
from git_reverse.core.logging import get_logger
from git_reverse.ingestion.cloner import RepositoryCloner
from git_reverse.ingestion.validator import RepositoryValidator
from git_reverse.storage.database import Database, Repository, RepositoryDAO, Session, SessionDAO
from git_reverse.tui.chat import ChatPane

log = get_logger(__name__)

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
"""


class SessionListItem(ListItem):
    """ListItem representing a session in the sidebar with type-safe session_id attribute."""
    session_id: str


# ── Sidebar ───────────────────────────────────────────────────────────────────
class Sidebar(Vertical):
    """Left panel: session list."""

    def compose(self) -> ComposeResult:
        yield Label("◈ Git Reverse", id="sidebar-title")
        yield Label("Recent Sessions", id="session-list-title")
        yield ListView(id="session-list")

    def populate_sessions(self, sessions: list[Session]) -> None:
        """Render session list items from database records."""
        session_list = self.query_one("#session-list", ListView)
        session_list.clear()
        if not sessions:
            session_list.append(ListItem(Label("No sessions yet.", classes="session-item"), id="none"))
            return
        for session in sessions:
            label = f"{session.id} [{session.mode}]"
            item = SessionListItem(Label(label, classes="session-item"))
            item.session_id = session.id  # Store session ID on node
            session_list.append(item)


# ── Main Panel ────────────────────────────────────────────────────────────────
class MainPanel(Vertical):
    """Right panel: welcomes dashboard or chat view."""

    def __init__(self, db: Database, settings: AppSettings) -> None:
        super().__init__()
        self._db = db
        self._settings = settings

    def compose(self) -> ComposeResult:
        yield Markdown(_WELCOME_TEXT, id="welcome-content")
        with Container(id="repo-input-container"):
            yield Label("Enter a GitHub URL or local path to begin:", id="repo-input-label")
            yield Input(
                placeholder="https://github.com/owner/repo  or  /path/to/local/repo",
                id="repo-input",
            )
        # Hidden by default, swapped when session starts
        chat_pane = ChatPane(self._db, self._settings.get_openrouter_key() or "", self._settings.default_model)
        chat_pane.display = False
        yield chat_pane


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
    """The root Textual application for Git Reverse."""

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
        self._repo_dao = RepositoryDAO(db)
        self.active_session_id: str | None = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="body"):
            yield Sidebar(id="sidebar")
            yield MainPanel(self._db, self._settings)
        yield StatusBar(id="status-bar")
        yield Footer()

    def on_mount(self) -> None:
        """Load initial data after the DOM is ready."""
        status = self.query_one(StatusBar)
        status.model_name = self._settings.default_model
        self.run_worker(self._load_recent_sessions())

    async def _load_recent_sessions(self) -> None:
        """Fetch recent sessions from SQLite and populate the sidebar."""
        try:
            sessions = await self._session_dao.list_recent(limit=15)
            self.query_one(Sidebar).populate_sessions(sessions)
        except Exception as exc:  # noqa: BLE001
            log.error("failed_to_load_sessions", error=str(exc))

    @on(ListView.Selected, "#session-list")
    def on_session_selected(self, event: ListView.Selected) -> None:
        """Handle session list selection."""
        item = event.item
        if not item or item.id == "none":
            return
        
        if isinstance(item, SessionListItem):
            self.run_worker(self._load_session_by_id(item.session_id))

    async def _load_session_by_id(self, session_id: str) -> None:
        """Switch to and display session by ID."""
        try:
            session = await self._session_dao.get_by_id(session_id)
            self.active_session_id = session.id
            
            status = self.query_one(StatusBar)
            status.session_id = session.id
            
            repo_name = "No repository"
            if session.repo_id:
                repo = await self._repo_dao.get_by_id(session.repo_id)
                if repo:
                    repo_name = repo.name
            status.repo_name = repo_name

            # Display Chat pane
            welcome = self.query_one("#welcome-content", Markdown)
            repo_box = self.query_one("#repo-input-container", Container)
            chat_pane = self.query_one(ChatPane)
            
            welcome.display = False
            repo_box.display = False
            chat_pane.display = True
            
            chat_pane.set_session(session.id, session.repo_id)
            self.notify(f"Loaded session {session.id}", severity="information")
        except Exception as exc:  # noqa: BLE001
            self.notify(f"Failed to load session: {exc}", severity="error")

    @on(Input.Submitted, "#repo-input")
    def on_repo_submitted(self, event: Input.Submitted) -> None:
        """Handle repository URL/path submission."""
        url = event.value.strip()
        if not url:
            return
        event.input.clear()
        self._run_analysis_pipeline(url)

    @work(exclusive=True)
    async def _run_analysis_pipeline(self, url_or_path: str) -> None:
        """Clones, validates, and runs AST analysis pipeline in the background."""
        self.notify("Starting repository ingestion...", title="Git Reverse")
        
        # 1. Create a Repository record in DB
        repo_id = str(uuid.uuid4())
        name = url_or_path.rstrip("/").split("/")[-1].replace(".git", "")
        
        repo = Repository(
            id=repo_id,
            url=url_or_path,
            name=name,
            analysis_status="running",
        )
        await self._repo_dao.upsert(repo)

        # Helper progress report callback
        async def progress_cb(phase: str, completed: int, total: int, msg: str) -> None:
            self.notify(f"[{completed}/{total}] {msg}", title="Analysis Pipeline")

        try:
            # 2. Clone
            cloner = RepositoryCloner(
                cache_dir=self._settings.repos_cache_path,
                timeout_seconds=self._settings.clone_timeout_seconds,
            )
            local_path = await cloner.clone(
                url_or_path,
                repo_id=repo_id,
                progress_callback=progress_cb,
            )

            # 3. Validate
            validator = RepositoryValidator(max_repo_size_mb=self._settings.max_repo_size_mb)
            val_result = validator.validate(local_path)

            # Update Repository local_path in DB
            repo.local_path = str(local_path)
            await self._repo_dao.upsert(repo)

            # 4. Parse AST and Build Dependency Graph
            pipeline = AnalysisPipeline(db=self._db, max_workers=self._settings.effective_workers)
            await pipeline.run(
                repo_id=repo_id,
                validation_result=val_result,
                progress_callback=progress_cb,
            )

            # 5. Pipeline completed. Spawn a new session for this repository
            session = await self._session_dao.create(
                model=self._settings.default_model,
                mode="explore",
                repo_id=repo_id,
                username=self._settings.username or None,
            )
            
            # Switch view to new session
            await self._load_session_by_id(session.id)
            await self._load_recent_sessions()

        except Exception as exc:  # noqa: BLE001
            log.error("analysis_pipeline_failed", error=str(exc))
            await self._repo_dao.update_status(repo_id, "failed", error=str(exc))
            self.notify(f"Pipeline failed: {exc}", severity="error")

    # ── Actions ───────────────────────────────────────────────────────────────
    async def action_new_session(self) -> None:
        """Create a new blank session."""
        session = await self._session_dao.create(
            model=self._settings.default_model,
            mode="explore",
            username=self._settings.username or None,
        )
        self.active_session_id = session.id
        await self._load_recent_sessions()
        await self._load_session_by_id(session.id)

    def action_toggle_theme(self) -> None:
        """Toggle between dark and light themes."""
        self.dark = not self.dark

    def action_command_palette(self) -> None:
        """Show the command palette."""
        from git_reverse.tui.palette import CommandPalette
        
        def handle_cmd(cmd: str | None) -> None:
            if not cmd:
                return
            if cmd == "settings":
                self.action_switch_model()
            elif cmd == "theme":
                self.action_toggle_theme()
            elif cmd == "new_session":
                self.run_worker(self.action_new_session())
            elif cmd == "resume":
                self.run_worker(self.action_resume_session())
            elif cmd == "help":
                self.action_show_help()
            elif cmd == "quit":
                self.exit()

        self.push_screen(CommandPalette(), handle_cmd)

    def action_switch_model(self) -> None:
        """Open settings screen (which manages model & keyring configuration)."""
        from git_reverse.tui.settings import SettingsScreen
        self.push_screen(SettingsScreen(self._settings))

    async def action_resume_session(self) -> None:
        """Resume the most recent session."""
        try:
            sessions = await self._session_dao.list_recent(limit=1)
            if sessions:
                await self._load_session_by_id(sessions[0].id)
            else:
                self.notify("No sessions to resume.", severity="warning")
        except Exception as exc:  # noqa: BLE001
            self.notify(f"Resume failed: {exc}", severity="error")

    async def action_save_session(self) -> None:
        """Save the current session state."""
        self.notify("Session saved.", severity="information")

    def action_show_help(self) -> None:
        """Display the help overlay."""
        self.notify("Press Ctrl+P to open the command palette.", severity="information")
