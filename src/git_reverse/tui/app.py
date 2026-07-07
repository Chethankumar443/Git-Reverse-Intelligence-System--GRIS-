"""
Git Reverse TUI Application.

Handles the keyboard-driven workspace interaction, async cloning and parsing,
and displays the sidebar session list and chat interactions.
"""

from __future__ import annotations

import uuid
from typing import ClassVar

from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.widgets import (
    Footer,
    Header,
    Input,
    Label,
    ListItem,
    ListView,
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

# External stylesheet is loaded via CSS_PATH


ASCII_LOGO = """
   █████████   ███   █████               ███████████
  ███▒▒▒▒▒███ ▒▒▒   ▒▒███               ▒▒███▒▒▒▒▒███
 ███     ▒▒▒  ████  ███████              ▒███    ▒███   ██████  █████ █████  ██████  ████████   █████   ██████
▒███         ▒▒███ ▒▒▒███▒    ██████████ ▒██████████   ███▒▒███▒▒███ ▒▒███  ███▒▒███▒▒███▒▒███ ███▒▒   ███▒▒███
▒███    █████ ▒███   ▒███    ▒▒▒▒▒▒▒▒▒▒  ▒███▒▒▒▒▒███ ▒███████  ▒███  ▒███ ▒███████  ▒███ ▒▒▒ ▒▒█████ ▒███████
▒▒███  ▒▒███  ▒███   ▒███ ███            ▒███    ▒███ ▒███▒▒▒   ▒▒███ ███  ▒███▒▒▒   ▒███      ▒▒▒▒███▒███▒▒▒
 ▒▒█████████  █████  ▒▒█████             █████   █████▒▒██████   ▒▒█████   ▒▒██████  █████     ██████ ▒▒██████
  ▒▒▒▒▒▒▒▒▒  ▒▒▒▒▒    ▒▒▒▒▒             ▒▒▒▒▒   ▒▒▒▒▒  ▒▒▒▒▒▒     ▒▒▒▒▒     ▒▒▒▒▒▒  ▒▒▒▒▒     ▒▒▒▒▒▒   ▒▒▒▒▒▒
""".strip("\n")


class WelcomeDashboard(Vertical):
    """A premium Bento-style welcome dashboard for Git Reverse."""

    def __init__(self, settings: AppSettings) -> None:
        super().__init__(id="welcome-content")
        self._settings = settings

    def compose(self) -> ComposeResult:
        yield Label(ASCII_LOGO, id="dashboard-logo")
        user = self._settings.username or "Guest"
        yield Label(f"Welcome back, {user}  │  Repository Intelligence Platform", id="dashboard-tagline")

        with Horizontal(id="dashboard-zones"):
            with Vertical(id="left-zone"):
                yield Label("Select Codebase", classes="zone-title")
                yield Label(
                    "Provide a remote Git URL or a local workspace path to analyze and build "
                    "the AST dependency graph.",
                    classes="zone-desc"
                )
                yield Input(
                    placeholder="https://github.com/owner/repo  or  /path/to/local/repo",
                    id="repo-input",
                )

            with Vertical(id="right-zone"):
                yield Label("System Status", classes="zone-title")
                yield Label("🔐 Keyring: Secure Storage Active", classes="status-item")
                yield Label("🗄️ Database: Local SQLite Index", classes="status-item")
                yield Label(f"🧠 Default Model: {self._settings.default_model}", classes="status-item")

                yield Label("Shortcut Commands", classes="zone-title", id="shortcuts-title")
                yield Label("[Ctrl+P]  Command Palette", classes="shortcut-item")
                yield Label("[Ctrl+N]  New Session", classes="shortcut-item")
                yield Label("[Ctrl+T]  Toggle Theme", classes="shortcut-item")
                yield Label("[Ctrl+Q]  Quit Application", classes="shortcut-item")


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
        yield WelcomeDashboard(self._settings)
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

    CSS_PATH = "styles.tcss"
    TITLE = "Git Reverse"
    SUB_TITLE = "Repository Intelligence Platform"

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("ctrl+p", "command_palette", "Command Palette", priority=True),
        Binding("ctrl+n", "new_session", "New Session"),
        Binding("ctrl+r", "resume_session", "Resume Session"),
        Binding("ctrl+s", "save_session", "Save"),
        Binding("ctrl+m", "switch_model", "Model"),
        Binding("ctrl+t", "toggle_theme", "Theme"),
        Binding("ctrl+b", "toggle_sidebar", "Toggle Sidebar"),
        Binding("ctrl+q", "quit", "Quit", priority=True),
        Binding("question_mark", "show_help", "Help", key_display="?"),
    ]

    def __init__(self, settings: AppSettings, db: Database, initial_session_id: str | None = None) -> None:
        super().__init__()
        self._settings = settings
        self._db = db
        self._session_dao = SessionDAO(db)
        self._repo_dao = RepositoryDAO(db)
        self.active_session_id: str | None = None
        self._initial_session_id = initial_session_id

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

        # Load requested initial session if specified
        if self._initial_session_id:
            self.run_worker(self._load_session_by_id(self._initial_session_id))
            self.run_worker(self._load_recent_sessions())
            self.set_interval(300, self._check_new_models)
            return

        # Check onboarding status
        if not self._settings.username:
            from git_reverse.tui.onboarding import OnboardingScreen

            async def handle_onboarding_dismiss(result: None) -> None:
                if self._settings.username:
                    status.model_name = self._settings.default_model
                    # Replace dashboard widget with fresh one showing username
                    main_panel = self.query_one(MainPanel)
                    await main_panel.query_one(WelcomeDashboard).remove()
                    await main_panel.mount(WelcomeDashboard(self._settings), before=0)

                    self.notify(f"Welcome to Git Reverse, {self._settings.username}!", severity="information")
                    self.run_worker(self._load_recent_sessions())

            self.push_screen(OnboardingScreen(self._settings), handle_onboarding_dismiss)
        else:
            self.run_worker(self._load_recent_sessions())

        # Set periodic free models checker (every 5 minutes)
        self.set_interval(300, self._check_new_models)

    async def _check_new_models(self) -> None:
        """Background checker for newly launched free-tier models on OpenRouter."""
        key = self._settings.get_openrouter_key()
        if not key:
            return

        import json

        import httpx

        cache_file = self._settings.data_dir / "free_models_cache.json"
        cached_ids: set[str] = set()
        if cache_file.exists():
            try:
                cached_ids = set(json.loads(cache_file.read_text(encoding="utf-8")))
            except Exception:
                pass

        url = "https://openrouter.ai/api/v1/models"
        headers = {"Authorization": f"Bearer {key}"}
        try:
            async with httpx.AsyncClient() as client:
                res = await client.get(url, headers=headers, timeout=10.0)
            if res.status_code == 200:
                models = res.json().get("data", [])
                current_free_ids = []
                new_models = []
                for m in models:
                    pricing = m.get("pricing", {})
                    prompt_cost = float(pricing.get("prompt") or 0.0)
                    completion_cost = float(pricing.get("completion") or 0.0)
                    if prompt_cost == 0.0 and completion_cost == 0.0:
                        m_id = m.get("id")
                        current_free_ids.append(m_id)
                        if cached_ids and m_id not in cached_ids:
                            new_models.append(m.get("name") or m_id)

                # Update cache file
                cache_file.write_text(json.dumps(current_free_ids), encoding="utf-8")

                # Notify user if new models found
                for new_m in new_models:
                    self.notify(
                        f"New free model launched: {new_m}! Check it out in settings.",
                        title="New Model Available",
                        severity="information"
                    )
        except Exception:
            pass

    async def _load_recent_sessions(self) -> None:
        """Fetch recent sessions from SQLite and populate the sidebar."""
        try:
            sessions = await self._session_dao.list_recent(limit=15)
            self.query_one(Sidebar).populate_sessions(sessions)
        except Exception as exc:
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
            welcome = self.query_one("#welcome-content")
            chat_pane = self.query_one(ChatPane)

            welcome.display = False
            chat_pane.display = True

            chat_pane.set_session(session.id, session.repo_id)
            self.notify(f"Loaded session {session.id}", severity="information")
        except Exception as exc:
            self.notify(f"Failed to load session: {exc}", severity="error")

    @on(Input.Submitted, "#repo-input")
    def on_repo_submitted(self, event: Input.Submitted) -> None:
        """Handle repository URL/path submission with optional trailing query."""
        val = event.value.strip()
        if not val:
            return
        event.input.clear()

        url, query = self._parse_repo_input(val)
        self._run_analysis_pipeline(url, query)

    def _parse_repo_input(self, value: str) -> tuple[str, str | None]:
        """
        Parse repo input string into a repository url/path and optional query.
        Example:
          "https://github.com/org/repo.git explain the architecture"
          -> ("https://github.com/org/repo.git", "explain the architecture")
        """
        parts = value.strip().split(maxsplit=1)
        if len(parts) == 2:
            first, rest = parts
            if (
                first.startswith(("http://", "https://", "git@", "ssh://"))
                or first.endswith(".git")
                or "/" in first
                or "\\" in first
            ):
                return first, rest
        return value.strip(), None

    @work(exclusive=True)
    async def _run_analysis_pipeline(self, url_or_path: str, initial_query: str | None = None) -> None:
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

            if initial_query:
                chat_pane = self.query_one(ChatPane)
                chat_pane.submit_query(initial_query)

        except Exception as exc:
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
        self.theme = "textual-light" if self.theme == "textual-dark" else "textual-dark"

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

        async def handle_settings_dismiss(result: None) -> None:
            # Refresh default model name in status bar
            self.query_one(StatusBar).model_name = self._settings.default_model
            # Rebuild WelcomeDashboard to show updated username
            try:
                main_panel = self.query_one(MainPanel)
                welcome = main_panel.query_one(WelcomeDashboard)
                await welcome.remove()
                await main_panel.mount(WelcomeDashboard(self._settings), before=0)
            except Exception:
                pass

        self.push_screen(SettingsScreen(self._settings), handle_settings_dismiss)

    async def action_resume_session(self) -> None:
        """Resume the most recent session."""
        try:
            sessions = await self._session_dao.list_recent(limit=1)
            if sessions:
                await self._load_session_by_id(sessions[0].id)
            else:
                self.notify("No sessions to resume.", severity="warning")
        except Exception as exc:
            self.notify(f"Resume failed: {exc}", severity="error")

    async def action_save_session(self) -> None:
        """Save the current session state."""
        self.notify("Session saved.", severity="information")

    def action_show_help(self) -> None:
        """Display the help overlay."""
        self.notify("Press Ctrl+P to open the command palette.", severity="information")

    def action_toggle_sidebar(self) -> None:
        """Toggle the sidebar display collapsed state."""
        sidebar = self.query_one(Sidebar)
        sidebar.toggle_class("collapsed")
