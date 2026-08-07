import asyncio
import re
from pathlib import Path

from textual.app import App, ComposeResult
from textual.widgets import (
    Input, Button, Static, Markdown, ProgressBar, OptionList, ListItem, Label,
)
from textual.containers import Vertical, Horizontal, ScrollableContainer
from textual.reactive import reactive
from textual.binding import Binding
from textual import on
from textual.events import Key
from rich.markup import escape
from rich.text import Text

from gitreverse.core.pipeline import AnalysisPipeline, PipelineProgress
from gitreverse.storage.database import DatabaseManager
from gitreverse.utils.config import load_config, save_config
from gitreverse.llm.client import LLMClient
from gitreverse.llm.context import ContextBuilder
from gitreverse.llm.prompts import (
    SYSTEM_PROMPT, EXPLAIN_REPO_PROMPT, EXPLAIN_ARCHITECTURE_PROMPT,
    EXPLAIN_FOLDER_PROMPT, DEPENDENCY_ANALYSIS_PROMPT, SUGGESTIONS_PROMPT,
)
from gitreverse.core.sessions import SessionManager, Session
from gitreverse.cli.setup import (
    is_setup_complete, validate_api_key, fetch_free_models, complete_setup,
    OPENROUTER_SIGNUP_URL,
)
from gitreverse.utils.logging import setup_logging, get_logger

logger = get_logger("cli.app")

COMMANDS = {
    "/help": "Show all available commands",
    "/settings": "View and modify settings (username, API key, model)",
    "/compact": "Summarize current session content",
    "/deep-dive": "Deep detailed analysis with full prompt",
    "/explain": "AI explains the repository purpose and structure",
    "/architecture": "AI explains architecture patterns and design",
    "/folders": "AI explains folder structure and organization",
    "/suggest": "AI suggests improvements and best practices",
    "/tree": "Show repository folder structure",
    "/readme": "Show README summary",
    "/deps": "List all dependencies by type",
    "/frameworks": "Show detected frameworks with evidence",
    "/languages": "Show language breakdown with file counts",
    "/sessions": "List all saved sessions",
    "/resume ID": "Resume a saved session by ID",
    "/save": "Save current session manually",
    "/export md": "Export analysis to Markdown file",
    "/export json": "Export analysis to JSON file",
    "/export txt": "Export analysis to TXT file",
    "/prompt": "Generate recreation prompt for this project",
    "/blueprint": "Generate development blueprint",
    "/clear": "Clear chat history",
    "/quit": "Exit and save session",
}

CSS = """
Screen { background: #0d1117; color: #e6edf3; }
#main-area { height: 100%; width: 100%; }
#progress-strip {
    height: auto; max-height: 6; background: #161b22;
    border-bottom: solid #30363d; padding: 0 2; display: none;
}
#progress-strip.visible { display: block; }
#progress-url { color: #58a6ff; text-style: bold; }
#progress-msg { color: #8b949e; }
#chat-viewport { height: 1fr; background: #0d1117; padding: 1 2; overflow-y: auto; }
#input-bar {
    height: 5; background: #161b22; border-top: solid #30363d; padding: 0 1; dock: bottom;
}
#mode-badge {
    width: 12; height: 3; content-align: center middle;
    background: #1f6feb; color: #ffffff; text-style: bold; margin: 0 1 0 0;
}
#mode-badge.query-mode { background: #2ea043; }
#main-input {
    width: 1fr; height: 3; background: #21262d;
    border: solid #30363d; color: #e6edf3;
}
#main-input:focus { border: solid #58a6ff; }
#submit-btn {
    width: 12; height: 3; margin-left: 1;
    background: #21262d; border: solid #30363d; color: #58a6ff;
}
#submit-btn:hover { background: #1f6feb; color: #ffffff; border: solid #1f6feb; }
#command-popup {
    height: auto; max-height: 15; background: #161b22;
    border: solid #30363d; padding: 1; display: none;
}
#command-popup.visible { display: block; }
.chat-user { color: #58a6ff; margin: 0 0 1 0; padding: 0 1; border-left: solid #1f6feb; }
.chat-system { color: #8b949e; margin: 0 0 1 0; }
.chat-result { margin: 0 0 1 0; }
.chat-error { color: #f85149; border-left: solid #da3633; padding: 0 1; margin: 0 0 1 0; }
#empty-state { height: 100%; content-align: center middle; color: #484f58; text-align: center; }

/* Setup Screen */
#setup-screen { height: 100%; width: 100%; }
#setup-container {
    height: 100%; width: 100%; padding: 1 2;
    overflow-y: auto; content-align: center top;
}
.setup-step {
    display: none; width: 100%; max-width: 100%;
    align: center top; padding: 0 2;
}
.setup-step.active { display: block; }
.setup-logo {
    width: 100%; text-align: center; margin-bottom: 0;
}
.setup-title {
    color: #58a6ff; text-style: bold; margin-bottom: 0;
    text-align: center; width: 100%;
}
.setup-subtitle {
    color: #8b949e; text-align: center; margin-bottom: 1;
    width: 100%;
}
.setup-label {
    color: #e6edf3; margin-top: 0; text-align: center; width: 100%;
}
.setup-hint {
    color: #484f58; margin-top: 0; margin-bottom: 0;
    text-align: center; width: 100%;
}
.setup-input {
    width: 80%; max-width: 60; min-width: 20;
    background: #21262d;
    border: solid #30363d; color: #e6edf3;
    text-align: center; content-align: center middle;
}
.setup-input:focus { border: solid #58a6ff; }
.setup-btn {
    width: 24; height: 3; margin-top: 1; margin-right: 1;
    background: #1f6feb; color: #ffffff; text-style: bold;
    content-align: center middle;
}
.setup-btn:hover { background: #388bfd; }
.setup-btn-skip {
    width: 16; height: 3; margin-top: 1;
    background: #21262d; color: #8b949e; border: solid #30363d;
    content-align: center middle;
}
.setup-btn-skip:hover { background: #30363d; color: #e6edf3; }
#btn-row-1, #btn-row-2, #btn-row-3 {
    width: 80%; max-width: 60; min-width: 20;
    align: center middle; content-align: center middle;
}
.setup-message {
    margin-top: 1; min-height: 2; text-align: center; width: 100%;
}
.setup-success { color: #2ea043; }
.setup-error { color: #f85149; }
.setup-info { color: #8b949e; }
.setup-link { color: #58a6ff; text-style: underline; text-align: center; width: 100%; }
.setup-progress { color: #484f58; text-align: center; width: 100%; margin-bottom: 1; }

/* Model Selector */
#model-selector {
    height: auto; max-height: 20; background: #161b22;
    border: solid #30363d; overflow-y: auto;
    width: 80%; max-width: 60; min-width: 20;
}
#model-selector:focus { border: solid #58a6ff; }
.model-item { padding: 0 1; color: #c9d1d9; height: auto; }
.model-item--highlight { background: #1f6feb; color: #ffffff; }
.model-item--selected { background: #2ea043; color: #ffffff; }
.model-current { color: #2ea043; text-style: bold; }
.model-free { color: #2ea043; }

/* Validating state */
.setup-input.validating { border: solid #d29922; }
.setup-input.valid { border: solid #2ea043; }
.setup-input.invalid { border: solid #f85149; }

/* Status Bar */
#status-bar {
    height: 1; background: #161b22; color: #8b949e;
    padding: 0 2; border-top: solid #21262d; dock: bottom;
}
.status-connected { color: #2ea043; }
.status-disconnected { color: #f85149; }
.status-model { color: #58a6ff; }
"""

ASCII_LOGO_WIDE = """
[bold #58a6ff] ██████╗ ██╗████████╗      ██████╗ ███████╗██╗   ██╗███████╗██████╗ ███████╗███████╗[/]
[bold #58a6ff]██╔════╝ ██║╚══██╔══╝      ██╔══██╗██╔════╝██║   ██║██╔════╝██╔══██╗██╔════╝██╔════╝[/]
[bold #58a6ff]██║  ███╗██║   ██║         ██████╔╝█████╗  ██║   ██║█████╗  ██████╔╝███████╗█████╗ [/]
[bold #58a6ff]██║   ██║██║   ██║         ██╔══██╗██╔══╝  ╚██╗ ██╔╝██╔══╝  ██╔══██╗╚════██║██╔══╝ [/]
[bold #58a6ff]╚██████╔╝██║   ██║         ██║  ██║███████╗ ╚████╔╝ ███████╗██║  ██║███████║███████╗[/]
[bold #58a6ff] ╚═════╝ ╚═╝   ╚═╝         ╚═╝  ╚═╝╚══════╝  ╚═══╝  ╚══════╝╚═╝  ╚═╝╚══════╝╚══════╝[/]"""

ASCII_LOGO_COMPACT = """
[bold #58a6ff]  ▗▄▄▖  ▄█▄▀▀▀▀  ▄  ▗▄▄▖ ▗▄▄▄▖▗▖  ▗▖▗▄▄▄▖▗▄▄▖  ▗▄▄▖▗▄▄▄▖[/]
[bold #58a6ff]  ▐▌▐▌   █  ▐▌   ▐▌ ▐▌   ▐▌   ▐▌  ▐▌▐▌   ▐▌ ▐▌▐▌   ▐▌   [/]
[bold #58a6ff]  ▐▌▐▌   █  ▐▛▀▘ ▐▌ ▐▌   ▐▛▀▀▘▐▌  ▐▌▐▛▀▀▘▐▛▀▚▖ ▝▀▚▖▐▛▀▀▘[/]
[bold #58a6ff]  ▐▙▟▯   █  ▐▌   ▐▙▄▟▯▝▚▄▄▖▐▙▄▄▖▐▙▟▯▗▄▄▄▖▐▌ ▐▌▗▄▄▟▯▐▙▄▄▖[/]"""


def _get_logo(console_width: int = 120) -> str:
    """Return the appropriate ASCII logo based on terminal width."""
    if console_width >= 95:
        return ASCII_LOGO_WIDE
    return ASCII_LOGO_COMPACT


# Keep ASCII_LOGO as an alias pointing to the wide logo for backward compat
ASCII_LOGO = ASCII_LOGO_WIDE


class CommandPopup(Static):
    def __init__(self, **kwargs):
        super().__init__("", **kwargs)
        self._visible = False
        self._commands: list[tuple[str, str]] = []

    def render(self) -> str:
        if not self._visible:
            return ""
        lines = ["[#58a6ff bold]COMMANDS[/]", "[#30363d]──────────────────────────[/]"]
        for cmd, desc in self._commands:
            lines.append(f"[#58a6ff]{cmd}[/]  [#8b949e]{desc}[/]")
        return "\n".join(lines)

    def show(self, filter_text: str = "") -> None:
        self._visible = True
        if filter_text:
            self._commands = [(k, v) for k, v in COMMANDS.items() if filter_text.lower() in k.lower()]
        else:
            self._commands = list(COMMANDS.items())
        self.refresh()

    def hide(self) -> None:
        self._visible = False
        self._commands = []
        self.refresh()

    def get_commands(self):
        return self._commands


class ModelSelector(Static):
    """Interactive model selector with keyboard and mouse support."""

    def __init__(self, models: list[dict], current_model: str = "", **kwargs):
        super().__init__("", **kwargs)
        self._models = models
        self._current_model = current_model
        self._selected_index = 0
        self._highlight_index = 0

    def render(self) -> str:
        if not self._models:
            return "[#8b949e]No models available[/]"

        lines = ["[#58a6ff bold]SELECT MODEL[/]", "[#484f58]──────────────────────────[/]"]
        lines.append("[#8b949e]Use ↑↓ arrows to navigate, Enter to select[/]\n")

        for i, m in enumerate(self._models):
            ctx = f"{m['context_length'] // 1024}K" if m.get('context_length') else "?"
            is_current = m["id"] == self._current_model
            is_highlighted = i == self._highlight_index

            if is_current:
                prefix = "[#2ea043] ✓ CURRENT[/]"
            elif is_highlighted:
                prefix = "[#58a6ff] ▸[/]"
            else:
                prefix = "  "

            name = m["name"][:45]
            # Use explicit hex colour tag — [model-context] is not valid Rich markup
            lines.append(f"{prefix} {name} [#8b949e]({ctx})[/#8b949e]")

        lines.append(f"\n[#8b949e]{len(self._models)} free models available — scroll for more[/]")
        return "\n".join(lines)

    def on_key(self, event: Key) -> None:
        if event.key == "up":
            self._highlight_index = max(0, self._highlight_index - 1)
            self.refresh()
        elif event.key == "down":
            self._highlight_index = min(len(self._models) - 1, self._highlight_index + 1)
            self.refresh()
        elif event.key == "enter":
            self._selected_index = self._highlight_index
            self.refresh()

    def get_selected(self) -> dict | None:
        if 0 <= self._selected_index < len(self._models):
            return self._models[self._selected_index]
        return None

    def get_highlighted(self) -> dict | None:
        if 0 <= self._highlight_index < len(self._models):
            return self._models[self._highlight_index]
        return None


class GitReverseApp(App):
    TITLE = "Git Reverse"
    CSS = CSS
    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit"),
        Binding("ctrl+k", "focus_input", "Focus"),
        Binding("ctrl+l", "clear_chat", "Clear"),
        Binding("escape", "cancel_analysis", "Cancel"),
    ]

    mode: reactive[str] = reactive("ANALYZE")
    active_repo: reactive[str] = reactive("")

    def __init__(self, resume_session: Session | None = None):
        super().__init__()
        self.config = load_config()
        self.db = DatabaseManager()
        self.pipeline = AnalysisPipeline(db=self.db)
        self.llm = LLMClient(api_key=self.config.llm.api_key, model=self.config.llm.model)
        self.context_builder = ContextBuilder(db=self.db)
        self.session_manager = SessionManager()
        self._active_tasks: dict[str, asyncio.Task] = {}
        self._repo_path: Path | None = None
        self._session = resume_session or self.session_manager.create_session()
        self._chat_history: list[dict] = []
        self._setup_step = 0
        self._setup_username = ""
        self._setup_api_key = ""
        self._setup_models: list[dict] = []
        self._model_selector: ModelSelector | None = None

    def compose(self) -> ComposeResult:
        if not self.config.user.is_setup_complete:
            yield from self._compose_setup()
        else:
            yield from self._compose_main()

    def _compose_setup(self):
        logo = _get_logo(self.console.width)
        with Vertical(id="setup-screen"):
            with ScrollableContainer(id="setup-container"):
                # Step 1: Username
                with Vertical(id="step-1", classes="setup-step active"):
                    yield Static(logo, classes="setup-logo")
                    yield Static("[#484f58]Step 1 of 4[/#484f58]", classes="setup-progress")
                    yield Static("Welcome to Git Reverse", classes="setup-title")
                    yield Static("Let's get you set up in a few seconds.", classes="setup-subtitle")
                    yield Static("What should we call you?", classes="setup-label")
                    yield Static("This name will be used to personalise your experience.", classes="setup-hint")
                    yield Input(placeholder="Enter your username", id="setup-input-1", classes="setup-input")
                    yield Horizontal(
                        Button("Continue →", id="btn-step-1", classes="setup-btn"),
                        id="btn-row-1"
                    )
                    yield Static("", id="msg-1", classes="setup-message")

                # Step 2: API Key
                with Vertical(id="step-2", classes="setup-step"):
                    yield Static(logo, classes="setup-logo")
                    yield Static("[#484f58]Step 2 of 4[/#484f58]", classes="setup-progress")
                    yield Static("Connect to OpenRouter", classes="setup-title")
                    yield Static("Get your free API key to enable AI features.", classes="setup-subtitle")
                    yield Static("1. Go to openrouter.ai and create an account", classes="setup-label")
                    yield Static("2. Create a new API key (free tier available)", classes="setup-label")
                    yield Static("3. Paste your key below", classes="setup-label")
                    yield Static(f"[link={OPENROUTER_SIGNUP_URL}]{OPENROUTER_SIGNUP_URL}[/link]", classes="setup-link")
                    yield Static("No credit card required for free models.", classes="setup-hint")
                    yield Input(placeholder="sk-or-v1-...", id="setup-input-2", classes="setup-input", password=True)
                    yield Horizontal(
                        Button("Validate & Continue →", id="btn-step-2", classes="setup-btn"),
                        Button("Skip for now", id="btn-skip-2", classes="setup-btn-skip"),
                        id="btn-row-2"
                    )
                    yield Static("", id="msg-2", classes="setup-message")
                    yield Static("[#484f58]ESC to go back[/#484f58]", classes="setup-hint")

                # Step 3: Model Selection
                with Vertical(id="step-3", classes="setup-step"):
                    yield Static(logo, classes="setup-logo")
                    yield Static("[#484f58]Step 3 of 4[/#484f58]", classes="setup-progress")
                    yield Static("Choose Your AI Model", classes="setup-title")
                    yield Static("Select a free model to power your analysis.", classes="setup-subtitle")
                    yield Static("Loading models...", id="models-status", classes="setup-info")
                    yield Static("", id="model-placeholder")
                    yield Horizontal(
                        Button("Confirm Selection", id="btn-step-3", classes="setup-btn"),
                        Button("Use Default", id="btn-default-3", classes="setup-btn-skip"),
                        id="btn-row-3"
                    )
                    yield Static("", id="msg-3", classes="setup-message")
                    yield Static("[#484f58]ESC to go back[/#484f58]", classes="setup-hint")

                # Step 4: Complete
                with Vertical(id="step-4", classes="setup-step"):
                    yield Static(logo, classes="setup-logo")
                    yield Static("[#484f58]Step 4 of 4[/#484f58]", classes="setup-progress")
                    yield Static("[#2ea043]✓[/#2ea043]  You're All Set!", classes="setup-title")
                    yield Static("Git Reverse is ready to analyse repositories.", classes="setup-subtitle")
                    yield Static("", id="final-summary")
                    yield Button("Start Analysing →", id="btn-finish", classes="setup-btn")

    def _compose_main(self):
        with Vertical(id="main-area"):
            with Vertical(id="progress-strip"):
                yield Static("", id="progress-url")
                yield Static("", id="progress-msg")
                yield ProgressBar(total=100, show_eta=False, id="progress-bar")
            with ScrollableContainer(id="chat-viewport"):
                yield Static(self._welcome_message(), id="empty-state")
            yield CommandPopup(id="command-popup")
            with Horizontal(id="input-bar"):
                yield Static("ANALYZE", id="mode-badge")
                yield Input(placeholder="GitHub URL + question, or / for commands", id="main-input")
                yield Button("Send", id="submit-btn")
        yield Static(self._status_text(), id="status-bar")

    def _welcome_message(self) -> str:
        name = self.config.user.username
        greeting = f"Welcome back, {name}!" if name else "Welcome!"
        model = self.config.llm.model.split("/")[-1] if self.config.llm.model else "none"
        connected = "[#2ea043]● Connected[/]" if self.llm.is_configured else "[#f85149]● Not connected[/]"
        logo = _get_logo(self.console.width)
        return (
            f"{logo}\n\n"
            f"[#e6edf3]{greeting}[/]\n"
            f"[#484f58]Paste a GitHub URL to analyse, or type [/#484f58][#58a6ff]/[/#58a6ff][#484f58] for commands.[/#484f58]\n"
            f"[#484f58]Model: [/#484f58][#58a6ff]{model}[/#58a6ff][#484f58]  |  {connected}[/#484f58]"
        )

    def _status_text(self) -> str:
        repo = self.active_repo or "No repo"
        model = self.config.llm.model.split("/")[-1] if self.config.llm.model else "none"
        connected = "Connected" if self.llm.is_configured else "Not connected"
        return f" GIT REVERSE v1.0.0  Model: {model}  Status: {connected}  Repo: {repo}"

    def _refresh_status(self) -> None:
        try:
            self.query_one("#status-bar", Static).update(self._status_text())
        except Exception:
            pass

    def watch_mode(self, value: str) -> None:
        try:
            badge = self.query_one("#mode-badge", Static)
            badge.update(value)
            if value == "QUERY":
                badge.add_class("query-mode")
                self.query_one("#main-input", Input).placeholder = "Ask about the repository or / for commands..."
            else:
                badge.remove_class("query-mode")
                self.query_one("#main-input", Input).placeholder = "GitHub URL + question, or / for commands"
        except Exception:
            pass
        self._refresh_status()

    def watch_active_repo(self, value: str) -> None:
        self._refresh_status()

    def action_focus_input(self) -> None:
        try:
            self.query_one("#main-input", Input).focus()
        except Exception:
            pass

    async def action_cancel_analysis(self) -> None:
        for task in list(self._active_tasks.values()):
            if not task.done():
                task.cancel()
        self._refresh_status()

    def action_clear_chat(self) -> None:
        try:
            viewport = self.query_one("#chat-viewport", ScrollableContainer)
            for child in list(viewport.children):
                child.remove()
            viewport.mount(Static(self._welcome_message(), id="empty-state"))
        except Exception:
            pass

    # ── Setup handlers ────────────────────────────────────────────────────

    def _show_step(self, step_num: int) -> None:
        for i in range(1, 5):
            try:
                step = self.query_one(f"#step-{i}", Vertical)
                if i == step_num:
                    step.add_class("active")
                else:
                    step.remove_class("active")
            except Exception:
                pass

    @on(Button.Pressed, "#btn-step-1")
    async def on_step1_continue(self, event: Button.Pressed) -> None:
        await self._handle_step1()

    @on(Input.Submitted, "#setup-input-1")
    async def on_step1_submit(self, event: Input.Submitted) -> None:
        await self._handle_step1()

    async def _handle_step1(self) -> None:
        value = self.query_one("#setup-input-1", Input).value.strip()
        msg = self.query_one("#msg-1", Static)
        if not value:
            msg.update("[#f85149]Please enter a username.[/]")
            return
        self._setup_username = value
        self._show_step(2)
        try:
            self.query_one("#setup-input-2", Input).focus()
        except Exception:
            pass

    @on(Button.Pressed, "#btn-step-2")
    async def on_step2_continue(self, event: Button.Pressed) -> None:
        await self._handle_step2()

    @on(Button.Pressed, "#btn-skip-2")
    async def on_step2_skip(self, event: Button.Pressed) -> None:
        self._setup_api_key = ""
        self._show_step(4)
        self._update_final_summary()

    @on(Input.Submitted, "#setup-input-2")
    async def on_step2_submit(self, event: Input.Submitted) -> None:
        await self._handle_step2()

    @on(Input.Changed, "#setup-input-2")
    async def on_step2_input_changed(self, event: Input.Changed) -> None:
        value = event.value.strip()
        input_widget = self.query_one("#setup-input-2", Input)
        msg = self.query_one("#msg-2", Static)

        if not value:
            input_widget.remove_class("valid")
            input_widget.remove_class("invalid")
            input_widget.remove_class("validating")
            msg.update("")
            return

        if value.startswith("sk-or-") and len(value) > 20:
            input_widget.add_class("validating")
            input_widget.remove_class("valid")
            input_widget.remove_class("invalid")
            msg.update("[#d29922]Validating API key...[/]")

            valid = await asyncio.get_event_loop().run_in_executor(None, lambda: validate_api_key(value))

            input_widget.remove_class("validating")
            if valid:
                self._setup_api_key = value
                input_widget.add_class("valid")
                input_widget.remove_class("invalid")
                msg.update("[#2ea043]✓ API key validated! Advancing in 1.5 seconds...[/]")
                # Brief pause so the user can read the success message before auto-advancing
                await asyncio.sleep(1.5)
                self._show_step(3)
                await self._load_models()
            else:
                input_widget.add_class("invalid")
                input_widget.remove_class("valid")
                msg.update("[#f85149]✗ Invalid API key. Check the key on openrouter.ai/keys and try again.[/]")
        else:
            input_widget.remove_class("valid")
            input_widget.remove_class("invalid")
            input_widget.remove_class("validating")
            msg.update("[#8b949e]Paste your OpenRouter API key (starts with sk-or-)[/]")

    async def _handle_step2(self) -> None:
        value = self.query_one("#setup-input-2", Input).value.strip()
        msg = self.query_one("#msg-2", Static)
        if not value:
            msg.update("[#f85149]Please enter an API key or skip.[/]")
            return
        msg.update("[#8b949e]Validating API key...[/]")
        valid = await asyncio.get_event_loop().run_in_executor(None, lambda: validate_api_key(value))
        if valid:
            self._setup_api_key = value
            msg.update("[#2ea043]API key validated successfully![/]")
            self._show_step(3)
            await self._load_models()
        else:
            msg.update("[#f85149]Invalid API key. Please check and try again.[/]")

    async def _load_models(self) -> None:
        status = self.query_one("#models-status", Static)
        status.update("[#8b949e]Loading free models from OpenRouter...[/]")
        self._setup_models = await asyncio.get_event_loop().run_in_executor(
            None, lambda: fetch_free_models(self._setup_api_key)
        )
        if self._setup_models:
            selector = ModelSelector(
                self._setup_models,
                current_model=self.config.llm.model,
            )
            try:
                placeholder = self.query_one("#model-placeholder", Static)
                placeholder.remove()
            except Exception:
                pass
            self.query_one("#step-3", Vertical).mount(selector, after=self.query_one("#models-status"))
            status.update(f"[#2ea043]{len(self._setup_models)} free models found[/]")
            try:
                selector.focus()
            except Exception:
                pass
        else:
            status.update("[#f85149]No free models found. Using default model.[/]")

    @on(Button.Pressed, "#btn-step-3")
    def on_step3_confirm(self, event: Button.Pressed) -> None:
        try:
            selector = self.query_one("#model-selector", ModelSelector)
            selected = selector.get_highlighted()
            if selected:
                self.config.llm.model = selected["id"]
        except Exception:
            pass
        self._show_step(4)
        self._update_final_summary()

    @on(Button.Pressed, "#btn-default-3")
    def on_step3_default(self, event: Button.Pressed) -> None:
        self._show_step(4)
        self._update_final_summary()

    def _update_final_summary(self) -> None:
        summary = self.query_one("#final-summary", Static)
        key_icon = "[#2ea043]✓[/#2ea043]" if self._setup_api_key else "[#f85149]✗[/#f85149]"
        key_status = "Configured" if self._setup_api_key else "Not set"
        model_short = self.config.llm.model.split("/")[-1] if self.config.llm.model else "default"
        lines = [
            "[#484f58]──────────────────────────────[/#484f58]",
            f"  [#8b949e]Username  [/#8b949e][#2ea043]✓[/#2ea043]  [#e6edf3]{self._setup_username}[/#e6edf3]",
            f"  [#8b949e]API Key   [/#8b949e]{key_icon}  [#e6edf3]{key_status}[/#e6edf3]",
            f"  [#8b949e]Model     [/#8b949e][#2ea043]✓[/#2ea043]  [#58a6ff]{model_short}[/#58a6ff]",
            "[#484f58]──────────────────────────────[/#484f58]",
            "",
            "[#484f58]Change these anytime with [/#484f58][#58a6ff]/settings[/#58a6ff]",
        ]
        summary.update("\n".join(lines))

    @on(Button.Pressed, "#btn-finish")
    def on_finish(self, event: Button.Pressed) -> None:
        self._finish_setup()

    def _finish_setup(self) -> None:
        self.config = complete_setup(self._setup_username, self._setup_api_key, self.config.llm.model)
        self.llm = LLMClient(api_key=self.config.llm.api_key, model=self.config.llm.model)
        try:
            self.query_one("#setup-screen").remove()
        except Exception:
            pass
        for widget in self._compose_main():
            self.mount(widget)
        try:
            self.query_one("#main-input", Input).focus()
        except Exception:
            pass

    # ── Main input handlers ───────────────────────────────────────────────

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "submit-btn":
            await self._handle_input()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "main-input":
            popup = self.query_one("#command-popup", CommandPopup)
            if popup._visible:
                self._execute_first_command()
            else:
                await self._handle_input()

    @on(Input.Changed, "#main-input")
    def on_input_changed(self, event: Input.Changed) -> None:
        text = event.value
        popup = self.query_one("#command-popup", CommandPopup)
        if text.startswith("/"):
            popup.show(text)
        else:
            popup.hide()

    def _execute_first_command(self) -> None:
        popup = self.query_one("#command-popup", CommandPopup)
        commands = popup.get_commands()
        if commands:
            self.query_one("#main-input", Input).value = commands[0][0]
            popup.hide()
            asyncio.get_event_loop().create_task(self._handle_input())

    async def _handle_input(self) -> None:
        text = self.query_one("#main-input", Input).value.strip()
        if not text:
            return
        self.query_one("#main-input", Input).value = ""
        self.query_one("#command-popup", CommandPopup).hide()
        if text.startswith("/"):
            await self._handle_command(text)
        else:
            await _handle_smart_input(self, text)

    async def _handle_command(self, cmd: str) -> None:
        parts = cmd.split(maxsplit=1)
        command = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""
        if command == "/help": _show_help(self)
        elif command == "/clear": self.action_clear_chat()
        elif command == "/quit": await _exit_with_session(self)
        elif command == "/settings": await _show_settings(self)
        elif command == "/compact": _compact_session(self)
        elif command == "/deep-dive": await _stream_llm(self, DEEP_DIVE_PROMPT)
        elif command == "/explain": await _stream_llm(self, EXPLAIN_REPO_PROMPT)
        elif command == "/architecture": await _stream_llm(self, EXPLAIN_ARCHITECTURE_PROMPT)
        elif command == "/folders": await _stream_llm(self, EXPLAIN_FOLDER_PROMPT)
        elif command == "/suggest": await _stream_llm(self, SUGGESTIONS_PROMPT)
        elif command == "/export": await _handle_export(self, args)
        elif command == "/tree": _show_tree(self)
        elif command == "/readme": _show_readme(self)
        elif command == "/deps": _show_deps(self)
        elif command == "/frameworks": _show_frameworks(self)
        elif command == "/languages": _show_languages(self)
        elif command == "/sessions": _show_sessions(self)
        elif command == "/resume": _resume_session(self, args)
        elif command == "/save": _save_session(self)
        elif command == "/prompt": _show_prompt(self)
        elif command == "/blueprint": _show_blueprint(self)
        elif command == "/config": await _handle_config(self, args)
        else: self._append_chat("error", f"Unknown command: {command}. Type /help.")

    def _remove_empty_state(self):
        try:
            self.query_one("#empty-state").remove()
        except Exception:
            pass

    def _append_chat(self, kind, content):
        self._remove_empty_state()
        self._chat_history.append({"role": kind, "content": content})
        viewport = self.query_one("#chat-viewport", ScrollableContainer)
        if kind == "user":
            widget = Static(f"[bold #58a6ff]> {escape(content)}[/]", classes="chat-user")
        elif kind == "system":
            widget = Static(f"[#8b949e]{content}[/]", classes="chat-system")
        elif kind == "error":
            widget = Static(f"[red]! {escape(content)}[/]", classes="chat-error")
        else:
            widget = Markdown(content, classes="chat-result")
        self.call_later(self._mount_widget, viewport, widget)

    async def _mount_widget(self, viewport, widget):
        await viewport.mount(widget)
        viewport.scroll_end(animate=False)


DEEP_DIVE_PROMPT = """Perform a comprehensive deep-dive analysis of this repository:
1. Project Overview  2. Architecture  3. Tech Stack
4. Key Components  5. Dependencies  6. Build & Run
7. Extension Points  8. Recreation Guide
Be thorough and cite specific files."""


async def _exit_with_session(app: GitReverseApp) -> None:
    app._session.messages = app._chat_history
    app.session_manager.save(app._session)
    exit_msg = app.session_manager.format_exit_screen(app._session)
    print("\n" + "=" * 70)
    print(exit_msg)
    print("=" * 70)
    app.exit()


def _show_help(app):
    lines = [
        "## Commands\n",
        "### AI Analysis",
        "- **/explain** - AI explains the repository purpose and structure",
        "- **/architecture** - AI explains architecture patterns and design",
        "- **/folders** - AI explains folder structure and organization",
        "- **/suggest** - AI suggests improvements and best practices",
        "- **/deep-dive** - Deep detailed analysis with full prompt",
        "",
        "### Session",
        "- **/compact** - Summarize current session content",
        "- **/save** - Save current session manually",
        "- **/sessions** - List all saved sessions",
        "- **/resume ID** - Resume a saved session by ID",
        "",
        "### Analysis",
        "- **/tree** - Show repository folder structure",
        "- **/readme** - Show README summary",
        "- **/deps** - List all dependencies by type",
        "- **/frameworks** - Show detected frameworks with evidence",
        "- **/languages** - Show language breakdown with file counts",
        "- **/prompt** - Generate recreation prompt for this project",
        "- **/blueprint** - Generate development blueprint",
        "",
        "### Config",
        "- **/settings** - View and modify settings",
        "- **/config api-key KEY** - Set OpenRouter API key",
        "- **/config model ID** - Change AI model",
        "- **/config username NAME** - Change username",
        "",
        "### Export",
        "- **/export md|json|txt** - Export analysis to file",
        "",
        "### Other",
        "- **/clear** - Clear chat history",
        "- **/quit** - Exit and save session",
    ]
    app._append_chat("result", "\n".join(lines))


async def _show_settings(app):
    key_status = "Set (encrypted)" if app.config.llm.api_key else "Not set"
    lines = [
        "## Settings\n",
        "### User",
        f"- **Username**: {app.config.user.username or 'Not set'}",
        "",
        "### LLM Configuration",
        f"- **API Key**: {key_status}",
        f"- **Model**: `{app.config.llm.model}`",
        f"- **Temperature**: {app.config.llm.temperature}",
        "",
        "### Commands",
        "- `/config api-key YOUR_KEY` - Set API key",
        "- `/config model MODEL_ID` - Change model",
        "- `/config username NAME` - Change username",
        "",
        "### OpenRouter Free Models",
        f"Get API key: {OPENROUTER_SIGNUP_URL}",
    ]

    if app.config.llm.api_key:
        lines.append("\n### Available Free Models\n")
        lines.append("_Loading models..._")
        app._append_chat("result", "\n".join(lines))

        models = await asyncio.get_event_loop().run_in_executor(
            None, lambda: fetch_free_models(app.config.llm.api_key)
        )
        if models:
            model_lines = []
            for i, m in enumerate(models[:20], 1):
                ctx = f"{m['context_length'] // 1024}K" if m.get('context_length') else "?"
                current = " ✓" if m["id"] == app.config.llm.model else ""
                model_lines.append(f"{i}. {m['name'][:45]} ({ctx}){current}")
            app._append_chat("result", "\n".join(model_lines) + "\n\n_Use `/config model MODEL_ID` to change._")
    else:
        app._append_chat("result", "\n".join(lines))


async def _handle_config(app, args):
    parts = args.split(maxsplit=1)
    if len(parts) < 2:
        app._append_chat("error", "Usage: /config [api-key|model|username] VALUE")
        return
    key, value = parts[0].lower(), parts[1].strip()
    if key == "api-key":
        app.config.llm.api_key = value
        save_config(app.config)
        app.llm = LLMClient(api_key=value, model=app.config.llm.model)
        app._append_chat("result", "API key updated and encrypted.")
    elif key == "model":
        app.config.llm.model = value
        save_config(app.config)
        app.llm = LLMClient(api_key=app.config.llm.api_key, model=value)
        app._append_chat("result", f"Model set to: `{value}`")
    elif key == "username":
        app.config.user.username = value
        save_config(app.config)
        app._append_chat("result", f"Username set to: {value}")
    else:
        app._append_chat("error", f"Unknown config key: {key}. Use api-key, model, or username.")


def _compact_session(app):
    if not app._chat_history:
        app._append_chat("system", "No content to summarize.")
        return
    topics = set()
    for msg in app._chat_history:
        if msg["role"] == "user":
            topics.update(w.lower() for w in msg["content"].split()[:5] if len(w) > 3)
    lines = [
        "## Session Summary\n",
        f"- **Session ID**: {app._session.id}",
        f"- **Repository**: {app._session.repo_name or 'None'}",
        f"- **Total Messages**: {len(app._chat_history)}",
        f"- **Your Questions**: {len([m for m in app._chat_history if m['role'] == 'user'])}",
        "",
        "### Topics Discussed",
    ]
    for t in list(topics)[:10]:
        lines.append(f"- {t}")
    app._append_chat("result", "\n".join(lines))


async def _stream_llm(app, task_prompt):
    if not app.active_repo:
        app._append_chat("error", "No repository analyzed yet.")
        return
    if not app.llm.is_configured:
        app._append_chat("error", "LLM not configured. Use: `/config api-key YOUR_KEY`")
        return
    app._remove_empty_state()
    viewport = app.query_one("#chat-viewport", ScrollableContainer)
    context = await asyncio.get_event_loop().run_in_executor(
        None, lambda: app.context_builder.build_context(app.active_repo, task_prompt))
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"{task_prompt}\n\n---\n\n{context}"}
    ]
    widget = Markdown("", classes="chat-result")
    await viewport.mount(widget)
    viewport.scroll_end(animate=False)
    resp = []
    async for chunk in app.llm.chat_stream(messages):
        resp.append(chunk)
        widget.update("".join(resp))
        viewport.scroll_end(animate=False)


def _show_sessions(app):
    sessions = app.session_manager.list_sessions(limit=10)
    if not sessions:
        app._append_chat("system", "No saved sessions found.")
        return
    lines = ["## Saved Sessions\n"]
    for s in sessions:
        created = s.created_at[:19].replace("T", " ")
        msg_count = len(s.messages)
        user_count = len([m for m in s.messages if m.get("role") == "user"])
        lines.append(f"- **{s.repo_name}** (`{s.id}`)")
        lines.append(f"  Created: {created} | Messages: {msg_count} | Questions: {user_count}")
        lines.append("")
    lines.append("Use `/resume SESSION_ID` to continue a session.")
    app._append_chat("result", "\n".join(lines))


def _resume_session(app, sid):
    sid = sid.strip()
    if not sid:
        app._append_chat("error", "Usage: /resume SESSION_ID")
        return
    session = app.session_manager.load(sid)
    if not session:
        app._append_chat("error", f"Session not found: {sid}")
        return
    app._session = session
    app._chat_history = session.messages or []
    if session.repo_name:
        app.active_repo = session.repo_name
        app.mode = "QUERY"
        app._repo_path = Path("~/.gitreverse/repos").expanduser() / session.repo_name
    app._remove_empty_state()
    viewport = app.query_one("#chat-viewport", ScrollableContainer)
    for child in list(viewport.children):
        child.remove()
    for msg in app._chat_history:
        role = msg.get("role", "system")
        content = msg.get("content", "")
        if role == "user":
            widget = Static(f"[bold #58a6ff]> {escape(content)}[/]", classes="chat-user")
        elif role == "error":
            widget = Static(f"[red]! {escape(content)}[/]", classes="chat-error")
        elif role == "system":
            widget = Static(f"[#8b949e]{content}[/]", classes="chat-system")
        else:
            widget = Markdown(content, classes="chat-result")
        viewport.mount(widget)
    viewport.scroll_end(animate=False)
    msg_count = len(app._chat_history)
    user_count = len([m for m in app._chat_history if m.get("role") == "user"])
    app._append_chat("system", f"Session resumed: {sid} | Repo: {session.repo_name} | {msg_count} messages ({user_count} questions) loaded")


def _save_session(app):
    app._session.messages = app._chat_history
    app.session_manager.save(app._session)
    app._append_chat("result", f"## Session Saved\n\nSession ID: `{app._session.id}`\nMessages: {len(app._chat_history)}")


def _show_tree(app):
    if not app._repo_path or not app._repo_path.exists():
        app._append_chat("error", "No repository cloned yet.")
        return
    from gitreverse.core.folder_tree import FolderTreeBuilder
    tree = FolderTreeBuilder().build(app._repo_path, max_depth=3)
    app._append_chat("result", f"## Folder Structure\n\n```\n{FolderTreeBuilder().to_string(tree)}\n```")


def _show_readme(app):
    if not app._repo_path or not app._repo_path.exists():
        app._append_chat("error", "No repository cloned yet.")
        return
    from gitreverse.parsers.readme_parser import ReadmeParser
    info = ReadmeParser().parse(app._repo_path)
    if not info:
        app._append_chat("error", "No README found.")
        return
    lines = [f"## {info.title}\n", info.description or ""]
    for s in info.sections[:5]:
        lines.extend([f"\n### {s['title']}", s['content'][:500]])
    app._append_chat("result", "\n".join(lines))


def _show_deps(app):
    from sqlmodel import select
    from gitreverse.models import Dependency, Repository
    with app.db.get_session() as sess:
        repo = sess.exec(select(Repository).where(Repository.url.contains(app.active_repo))).first()
        if not repo:
            app._append_chat("error", "No analysis data found.")
            return
        deps = sess.exec(select(Dependency).where(Dependency.repository_id == repo.id)).all()
        if not deps:
            app._append_chat("system", "No dependencies found.")
            return
        by_type = {}
        for d in deps:
            by_type.setdefault(d.type, []).append(d)
        lines = [f"## Dependencies ({len(deps)} total)\n"]
        for dt, ds in by_type.items():
            lines.append(f"### {dt.title()} ({len(ds)})")
            for d in ds[:20]:
                lines.append(f"- `{d.package_name}` {d.version or ''}")
            lines.append("")
        app._append_chat("result", "\n".join(lines))


def _show_frameworks(app):
    from sqlmodel import select
    from gitreverse.models import Framework, Repository
    with app.db.get_session() as sess:
        repo = sess.exec(select(Repository).where(Repository.url.contains(app.active_repo))).first()
        if not repo:
            app._append_chat("error", "No analysis data found.")
            return
        fws = sess.exec(select(Framework).where(Framework.repository_id == repo.id)).all()
        if not fws:
            app._append_chat("system", "No frameworks detected.")
            return
        lines = ["## Detected Frameworks\n"]
        for fw in fws:
            lines.append(f"### {fw.name} {fw.version or ''}")
            if fw.evidence:
                for k, v in fw.evidence.items():
                    lines.append(f"- {k}: `{v}`")
            lines.append("")
        app._append_chat("result", "\n".join(lines))


def _show_languages(app):
    from sqlmodel import select
    from gitreverse.models import File, Repository
    with app.db.get_session() as sess:
        repo = sess.exec(select(Repository).where(Repository.url.contains(app.active_repo))).first()
        if not repo:
            app._append_chat("error", "No analysis data found.")
            return
        files = sess.exec(select(File).where(File.repository_id == repo.id)).all()
        lc = {}
        for f in files:
            lc[f.language] = lc.get(f.language, 0) + 1
        lines = ["## Language Breakdown\n"]
        for lang, cnt in sorted(lc.items(), key=lambda x: -x[1]):
            bar = "#" * min(cnt, 30)
            lines.append(f"- **{lang}**: {cnt} files `{bar}`")
        lines.append(f"\n**Total**: {len(files)} files")
        app._append_chat("result", "\n".join(lines))


def _show_prompt(app):
    if not app.active_repo:
        app._append_chat("error", "No repository analyzed yet.")
        return
    from gitreverse.core.prompts import PromptGenerator
    data = _gather_export_data(app)
    prompt = PromptGenerator().generate_recreation_prompt(data)
    app._append_chat("result", f"## Recreation Prompt\n\n```\n{prompt}\n```")


def _show_blueprint(app):
    if not app.active_repo:
        app._append_chat("error", "No repository analyzed yet.")
        return
    from gitreverse.core.prompts import PromptGenerator
    data = _gather_export_data(app)
    blueprint = PromptGenerator().generate_blueprint(data)
    app._append_chat("result", f"## Development Blueprint\n\n```\n{blueprint}\n```")


async def _handle_export(app, fmt):
    if not app.active_repo:
        app._append_chat("error", "No repository analyzed yet.")
        return
    fmt = fmt.strip().lower()
    if fmt not in ("md", "json", "txt"):
        app._append_chat("error", "Usage: /export [md|json|txt]")
        return
    data = await asyncio.get_event_loop().run_in_executor(None, lambda: _gather_export_data(app))
    if not data:
        app._append_chat("error", "Failed to gather export data.")
        return
    from gitreverse.core.export import Exporter
    out_dir = Path("~/.gitreverse/exports").expanduser()
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{app.active_repo}.{fmt}"
    try:
        e = Exporter()
        {"md": e.export_markdown, "json": e.export_json, "txt": e.export_txt}[fmt](data, out)
        app._append_chat("result", f"## Exported\n\nSaved to: `{out}`")
    except Exception as ex:
        app._append_chat("error", f"Export failed: {ex}")


def _gather_export_data(app):
    from sqlmodel import select
    from gitreverse.models import Framework, Dependency, File, Repository
    with app.db.get_session() as sess:
        repo = sess.exec(select(Repository).where(Repository.url.contains(app.active_repo))).first()
        if not repo:
            return {}
        rid = repo.id
        fws = sess.exec(select(Framework).where(Framework.repository_id == rid)).all()
        deps = sess.exec(select(Dependency).where(Dependency.repository_id == rid)).all()
        files = sess.exec(select(File).where(File.repository_id == rid)).all()
        lc = {}
        for f in files:
            lc[f.language] = lc.get(f.language, 0) + 1
        return {
            "repo_name": app.active_repo, "repo_url": repo.url,
            "commit_hash": repo.commit_hash,
            "analyzed_at": repo.last_analysis_date.isoformat() if repo.last_analysis_date else "",
            "frameworks": [{"name": fw.name, "version": fw.version} for fw in fws],
            "dependencies": [{"package_name": d.package_name, "version": d.version, "type": d.type} for d in deps],
            "languages": lc, "symbols": [], "folder_tree": "", "readme": {},
        }


async def _handle_smart_input(app, text):
    url_match = re.match(r'(https?://\S+|git@\S+)(.*)', text)
    if url_match:
        url = url_match.group(1).strip().rstrip("'\"")
        query = url_match.group(2).strip()
        if query:
            app._remove_empty_state()
            app._append_chat("user", text)
            app._append_chat("system", f"Analyzing {url} and processing your request...")
            await _run_analysis_and_query(app, url, query)
        else:
            await _start_analysis(app, url)
    else:
        if app.mode == "QUERY" and app.active_repo:
            app._append_chat("user", text)
            if app.llm.is_configured:
                await _stream_query(app, text)
            else:
                app._append_chat("system", "_Querying knowledge graph..._")
                answer = await asyncio.get_event_loop().run_in_executor(None, lambda: _query_db(app, text))
                app._append_chat("result", answer)
        else:
            app._append_chat("error", "Paste a GitHub URL to analyze, or analyze a repo first.")


async def _run_analysis_and_query(app, url, query):
    try:
        app.query_one("#progress-strip").add_class("visible")
        app.query_one("#progress-url", Static).update(url)
    except Exception:
        pass
    try:
        async for progress in app.pipeline.run(url):
            try:
                app.query_one("#progress-msg", Static).update(f"[{progress.stage.upper()}] {progress.message}")
                app.query_one("#progress-bar", ProgressBar).progress = progress.percent
            except Exception:
                pass
            if progress.stage == "complete":
                app._repo_path = Path("~/.gitreverse/repos").expanduser() / url.rstrip("/").split("/")[-1]
                app.active_repo = url.rstrip("/").split("/")[-1]
                app.mode = "QUERY"
                app._session.repo_url = url
                app._session.repo_name = app.active_repo
            elif progress.stage == "error":
                app._append_chat("error", progress.message)
                return
    except Exception as e:
        app._append_chat("error", f"Analysis failed: {e}")
        return
    finally:
        try:
            app.query_one("#progress-strip").remove_class("visible")
        except Exception:
            pass
    if app.active_repo and app.llm.is_configured:
        custom_prompt = f"The user asks: {query}\n\nBased on the analysis data, provide a helpful and detailed response. If they want to build something similar, provide a step-by-step plan. If they want to understand the architecture, explain it clearly with file references."
        await _stream_llm_with_context(app, custom_prompt)
    elif app.active_repo:
        app._append_chat("result", f"## Analysis Complete: {app.active_repo}\n\nLLM not configured. Use `/config api-key` to enable AI responses.")


async def _stream_llm_with_context(app, task_prompt):
    if not app.active_repo or not app.llm.is_configured:
        return
    app._remove_empty_state()
    viewport = app.query_one("#chat-viewport", ScrollableContainer)
    context = await asyncio.get_event_loop().run_in_executor(
        None, lambda: app.context_builder.build_context(app.active_repo, task_prompt))
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"{task_prompt}\n\n---\n\n{context}"}
    ]
    widget = Markdown("", classes="chat-result")
    await viewport.mount(widget)
    viewport.scroll_end(animate=False)
    resp = []
    async for chunk in app.llm.chat_stream(messages):
        resp.append(chunk)
        widget.update("".join(resp))
        viewport.scroll_end(animate=False)


async def _stream_query(app, query):
    context = await asyncio.get_event_loop().run_in_executor(
        None, lambda: app.context_builder.build_query_context(app.active_repo, query))
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Question: {query}\n\n---\n\n{context}"}
    ]
    app._remove_empty_state()
    viewport = app.query_one("#chat-viewport", ScrollableContainer)
    widget = Markdown("", classes="chat-result")
    await viewport.mount(widget)
    viewport.scroll_end(animate=False)
    resp = []
    async for chunk in app.llm.chat_stream(messages):
        resp.append(chunk)
        widget.update("".join(resp))
        viewport.scroll_end(animate=False)


async def _start_analysis(app, url):
    url = url.split()[0].rstrip("'\"")
    if not (url.startswith("http") or url.startswith("git@")):
        app._append_chat("error", f"Invalid URL: `{url}`")
        return
    if url in app._active_tasks and not app._active_tasks[url].done():
        app._append_chat("system", "Already analyzing this repository.")
        return
    app._remove_empty_state()
    app._append_chat("user", f"Analyze {url}")
    task = asyncio.create_task(_run_pipeline(app, url))
    app._active_tasks[url] = task
    app._refresh_status()


async def _run_pipeline(app, url):
    try:
        app.query_one("#progress-strip").add_class("visible")
        app.query_one("#progress-url", Static).update(url)
    except Exception:
        pass
    try:
        async for progress in app.pipeline.run(url):
            try:
                app.query_one("#progress-msg", Static).update(f"[{progress.stage.upper()}] {progress.message}")
                app.query_one("#progress-bar", ProgressBar).progress = progress.percent
            except Exception:
                pass
            if progress.stage == "complete":
                app._repo_path = Path("~/.gitreverse/repos").expanduser() / url.rstrip("/").split("/")[-1]
                app.active_repo = url.rstrip("/").split("/")[-1]
                app.mode = "QUERY"
                app._session.repo_url = url
                app._session.repo_name = app.active_repo
                app._remove_empty_state()
                app._append_chat("result", f"## Analysis Complete: {app.active_repo}\n\n{progress.message}\n\nType **/** for commands or ask questions.")
            elif progress.stage == "error":
                app._append_chat("error", progress.message)
    except asyncio.CancelledError:
        app._append_chat("system", "Analysis cancelled.")
    except Exception as e:
        app._append_chat("error", str(e))
    finally:
        app._active_tasks.pop(url, None)
        try:
            app.query_one("#progress-strip").remove_class("visible")
        except Exception:
            pass
        app._refresh_status()


def _query_db(app, query):
    q = query.lower()
    from sqlmodel import select
    from gitreverse.models import Framework, Dependency, File, Repository
    with app.db.get_session() as sess:
        repo = sess.exec(select(Repository).where(Repository.url.contains(app.active_repo))).first()
        if not repo:
            return f"No analysis data found for `{app.active_repo}`."
        rid = repo.id
        if any(w in q for w in ("framework", "stack", "library", "use", "built with")):
            fws = sess.exec(select(Framework).where(Framework.repository_id == rid)).all()
            if not fws:
                return "No frameworks detected."
            lines = ["## Detected Frameworks\n"]
            for fw in fws:
                lines.append(f"**{fw.name}** {fw.version or ''}")
            return "\n".join(lines)
        elif any(w in q for w in ("depend", "package", "npm", "pip")):
            deps = sess.exec(select(Dependency).where(Dependency.repository_id == rid)).all()
            if not deps:
                return "No dependencies found."
            lines = [f"## Dependencies ({len(deps)} total)\n"]
            for d in deps[:20]:
                lines.append(f"- `{d.package_name}` {d.version or ''}")
            return "\n".join(lines)
        else:
            fws = sess.exec(select(Framework).where(Framework.repository_id == rid)).all()
            deps = sess.exec(select(Dependency).where(Dependency.repository_id == rid)).all()
            files = sess.exec(select(File).where(Framework.repository_id == rid)).all()
            fw_names = ", ".join(f.name for f in fws) or "none detected"
            return (
                f"## Repository Summary: `{app.active_repo}`\n\n"
                f"- **Frameworks**: {fw_names}\n"
                f"- **Dependencies**: {len(deps)} packages\n"
                f"- **Source Files**: {len(files)}\n"
                f"- **Commit**: `{repo.commit_hash[:8]}`\n\n"
                f"_Type /help for available commands._"
            )


def main() -> None:
    import argparse
    import importlib.metadata

    try:
        _version = importlib.metadata.version("gitreverse")
    except importlib.metadata.PackageNotFoundError:
        _version = "1.0.0"

    parser = argparse.ArgumentParser(
        prog="gitreverse",
        description="Git Reverse — reverse-engineer any GitHub repository with AI.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  gitreverse                    Launch the interactive TUI\n"
            "  gitreverse --reset-setup      Clear saved credentials and re-run setup\n"
        ),
    )
    parser.add_argument(
        "--version", "-V",
        action="version",
        version=f"gitreverse {_version}",
    )
    parser.add_argument(
        "--reset-setup",
        action="store_true",
        help="Reset all saved configuration and re-run the setup wizard",
    )
    args = parser.parse_args()

    setup_logging()

    if args.reset_setup:
        config = load_config()
        config.user.is_setup_complete = False
        config.user.username = ""
        config.llm.api_key = ""
        save_config(config)
        print("Setup reset. Re-launching Git Reverse setup wizard...")

    # GitReverseApp.__init__ calls load_config() internally; no need to duplicate here.
    app = GitReverseApp()
    try:
        app.run()
    except KeyboardInterrupt:
        pass
    finally:
        if app._chat_history:
            app._session.messages = app._chat_history
            app.session_manager.save(app._session)
            print("\n" + "=" * 70)
            print(app.session_manager.format_exit_screen(app._session))
            print("=" * 70)


if __name__ == "__main__":
    main()
