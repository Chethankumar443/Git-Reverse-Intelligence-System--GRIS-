import asyncio
from typing import AsyncIterator

from textual.app import App, ComposeResult
from textual.widgets import (
    Header, Footer, Input, Button, Label,
    Static, Markdown, ListView, ListItem, ProgressBar,
)
from textual.containers import Vertical, Horizontal, ScrollableContainer
from textual.reactive import reactive
from textual.binding import Binding
from rich.markup import escape
from rich.text import Text

from gitreverse.core.pipeline import AnalysisPipeline, PipelineProgress
from gitreverse.storage.database import DatabaseManager
from gitreverse.utils.logging import setup_logging, get_logger

logger = get_logger("cli.app")

# ──────────────────────────────────────────────────────────────────────────────
# CSS — Dark editorial tech aesthetic
# ──────────────────────────────────────────────────────────────────────────────

CSS = """
/* Root */
Screen {
    background: #0d1117;
    color: #e6edf3;
    layout: grid;
    grid-size: 2;
    grid-columns: 28 1fr;
}

/* ── Left Sidebar ─────────────────────────────────────────── */
#sidebar {
    background: #161b22;
    border-right: solid #30363d;
    height: 100%;
    padding: 1;
    overflow-y: auto;
}

#sidebar-title {
    color: #58a6ff;
    text-style: bold;
    padding-bottom: 1;
    border-bottom: solid #21262d;
    margin-bottom: 1;
}

.section-header {
    color: #8b949e;
    text-style: bold;
    padding: 0 0 0 0;
    margin-top: 1;
    text-transform: uppercase;
}

.sidebar-item {
    color: #c9d1d9;
    padding: 0;
    background: transparent;
}

.sidebar-item:hover {
    background: #21262d;
}

.sidebar-tag {
    background: #1f6feb;
    color: #ffffff;
    padding: 0 1;
}

.sidebar-tag-green {
    background: #2ea043;
    color: #ffffff;
    padding: 0 1;
}

/* ── Main Panel ────────────────────────────────────────────── */
#main-panel {
    height: 100%;
    layout: vertical;
}

/* Progress strip at top of main panel */
#progress-strip {
    height: auto;
    max-height: 8;
    background: #161b22;
    border-bottom: solid #30363d;
    padding: 0 2;
    display: none;
}

#progress-strip.visible {
    display: block;
}

#progress-url {
    color: #58a6ff;
    text-style: bold;
}

#progress-msg {
    color: #8b949e;
}

/* Chat / results viewport */
#chat-viewport {
    height: 1fr;
    background: #0d1117;
    padding: 1 2;
    overflow-y: auto;
}

/* Input bar at bottom */
#input-bar {
    height: 5;
    background: #161b22;
    border-top: solid #30363d;
    padding: 1 2;
    align: left middle;
}

#mode-badge {
    width: 12;
    height: 3;
    content-align: center middle;
    background: #1f6feb;
    color: #ffffff;
    text-style: bold;
    margin-right: 1;
}

#mode-badge.query-mode {
    background: #2ea043;
}

#main-input {
    width: 1fr;
    height: 3;
    background: #21262d;
    border: solid #30363d;
    color: #e6edf3;
}

#main-input:focus {
    border: solid #58a6ff;
}

#submit-btn {
    width: 10;
    height: 3;
    margin-left: 1;
    background: #21262d;
    border: solid #30363d;
    color: #58a6ff;
}

#submit-btn:hover {
    background: #1f6feb;
    color: #ffffff;
    border: solid #1f6feb;
}

/* Status bar */
#status-bar {
    height: 1;
    background: #161b22;
    color: #8b949e;
    padding: 0 2;
    border-top: solid #21262d;
    column-span: 2;
}

/* Chat messages */
.chat-user {
    color: #58a6ff;
    margin: 1 0;
    padding: 0 1;
    border-left: solid #1f6feb;
}

.chat-system {
    color: #8b949e;
    margin: 0 0 1 0;
}

.chat-result {
    margin: 1 0 2 0;
}

.chat-error {
    color: #f85149;
    border-left: solid #da3633;
    padding: 0 1;
    margin: 1 0;
}

/* Empty state */
#empty-state {
    height: 100%;
    align: center middle;
    color: #30363d;
}
"""

# ──────────────────────────────────────────────────────────────────────────────
# Sidebar Widget
# ──────────────────────────────────────────────────────────────────────────────

class Sidebar(Static):
    def __init__(self, **kwargs):
        super().__init__("", **kwargs)
        self._repo_name: str = "—"
        self._frameworks: list[str] = []
        self._languages: list[str] = []
        self._stats: dict = {}

    def render(self) -> str:
        lines = []
        lines.append("[bold #58a6ff]GIT REVERSE[/]")
        lines.append("[#21262d]────────────────────────[/]")
        lines.append("")
        lines.append("[#8b949e bold]REPOSITORY[/]")
        lines.append(f"[#c9d1d9] {self._repo_name}[/]")

        if self._languages:
            lines.append("")
            lines.append("[#8b949e bold]LANGUAGES[/]")
            for lang in self._languages[:6]:
                lines.append(f"[#c9d1d9] ○ {lang}[/]")

        if self._frameworks:
            lines.append("")
            lines.append("[#8b949e bold]FRAMEWORKS[/]")
            for fw in self._frameworks[:6]:
                lines.append(f"[#2ea043] ✓ {fw}[/]")

        if self._stats:
            lines.append("")
            lines.append("[#8b949e bold]ANALYSIS[/]")
            for k, v in self._stats.items():
                lines.append(f"[#8b949e] {k}:[/] [#c9d1d9]{v}[/]")

        lines.append("")
        lines.append("[#21262d]────────────────────────[/]")
        lines.append("[#8b949e]KEYBINDINGS[/]")
        lines.append("[#8b949e] Ctrl+K  Focus input[/]")
        lines.append("[#8b949e] Ctrl+L  Clear chat[/]")
        lines.append("[#8b949e] Esc     Cancel[/]")
        lines.append("[#8b949e] Ctrl+Q  Quit[/]")

        return "\n".join(lines)

    def update_repo(self, name: str, frameworks: list[str], languages: list[str], stats: dict) -> None:
        self._repo_name = name
        self._frameworks = frameworks
        self._languages = languages
        self._stats = stats
        self.refresh()


# ──────────────────────────────────────────────────────────────────────────────
# Main App
# ──────────────────────────────────────────────────────────────────────────────

class GitReverseApp(App):
    TITLE = "Git Reverse"
    CSS = CSS
    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit"),
        Binding("ctrl+k", "focus_input", "Focus"),
        Binding("ctrl+l", "clear_chat", "Clear"),
        Binding("escape", "cancel_analysis", "Cancel"),
    ]

    # Reactive state
    mode: reactive[str] = reactive("ANALYZE")   # ANALYZE | QUERY
    active_repo: reactive[str] = reactive("")

    def __init__(self):
        super().__init__()
        self.db = DatabaseManager()
        self.pipeline = AnalysisPipeline(db=self.db)
        self._active_tasks: dict[str, asyncio.Task] = {}
        self._chat_lines: list[str] = []
        self._analyzed_repos: list[dict] = []

    # ── Compose ──────────────────────────────────────────────────────────────

    def compose(self) -> ComposeResult:
        # Sidebar
        yield Sidebar(id="sidebar")

        # Main panel
        with Vertical(id="main-panel"):
            # Progress strip (hidden when idle)
            with Vertical(id="progress-strip"):
                yield Static("", id="progress-url")
                yield Static("", id="progress-msg")
                yield ProgressBar(total=100, show_eta=False, id="progress-bar")

            # Chat viewport
            with ScrollableContainer(id="chat-viewport"):
                yield Static(
                    "[#30363d]Paste a GitHub URL to analyze a repository,\nor ask a question after analysis completes.[/]",
                    id="empty-state"
                )

            # Input bar
            with Horizontal(id="input-bar"):
                yield Static("ANALYZE", id="mode-badge")
                yield Input(
                    placeholder="https://github.com/owner/repo",
                    id="main-input",
                )
                yield Button("⏎ Send", id="submit-btn")

        # Status bar spans full width
        yield Static(self._status_text(), id="status-bar")

    # ── Status ───────────────────────────────────────────────────────────────

    def _status_text(self) -> str:
        repo_info = f"  {self.active_repo}" if self.active_repo else "  No repo loaded"
        task_count = sum(1 for t in self._active_tasks.values() if not t.done())
        tasks_info = f"  [{task_count} active]" if task_count else ""
        return f" GIT REVERSE  v1.0.0{tasks_info}  │  Mode: {self.mode}{repo_info}"

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
                badge.remove_class("analyze-mode")
                self.query_one("#main-input", Input).placeholder = "Ask a question about the repository…"
            else:
                badge.remove_class("query-mode")
                badge.add_class("analyze-mode")
                self.query_one("#main-input", Input).placeholder = "https://github.com/owner/repo"
        except Exception:
            pass
        self._refresh_status()

    def watch_active_repo(self, value: str) -> None:
        self._refresh_status()

    # ── Actions ──────────────────────────────────────────────────────────────

    def action_focus_input(self) -> None:
        self.query_one("#main-input", Input).focus()

    async def action_cancel_analysis(self) -> None:
        for url, task in list(self._active_tasks.items()):
            if not task.done():
                task.cancel()
        self._refresh_status()

    def action_clear_chat(self) -> None:
        self._chat_lines.clear()
        try:
            viewport = self.query_one("#chat-viewport", ScrollableContainer)
            for child in list(viewport.children):
                child.remove()
            viewport.mount(Static(
                "[#30363d]Chat cleared. Paste a GitHub URL to analyze a repository.[/]",
                id="empty-state"
            ))
        except Exception:
            pass

    # ── Event Handlers ───────────────────────────────────────────────────────

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "submit-btn":
            await self._handle_input()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "main-input":
            await self._handle_input()

    # ── Input Router ─────────────────────────────────────────────────────────

    async def _handle_input(self) -> None:
        text = self.query_one("#main-input", Input).value.strip()
        if not text:
            return
        self.query_one("#main-input", Input).value = ""

        # Route based on mode
        if self.mode == "ANALYZE" or text.startswith("http"):
            # Auto-detect URL
            if text.startswith("http") or text.startswith("git@"):
                await self._start_analysis(text)
            else:
                # In QUERY mode with a non-URL
                await self._handle_query(text)
        else:
            await self._handle_query(text)

    # ── Analysis Pipeline ─────────────────────────────────────────────────────

    async def _start_analysis(self, url: str) -> None:
        # Clean URL — strip trailing text
        url = url.split()[0].rstrip("'\"")

        if not (url.startswith("http") or url.startswith("git@")):
            self._append_chat("error", f"Invalid URL: `{url}`")
            return

        if url in self._active_tasks and not self._active_tasks[url].done():
            self._append_chat("system", f"⚠ Already analyzing `{url}`")
            return

        self._remove_empty_state()
        self._append_chat("user", f"Analyze `{url}`")

        task = asyncio.create_task(self._run_pipeline(url))
        self._active_tasks[url] = task
        self._refresh_status()

    async def _run_pipeline(self, url: str) -> None:
        # Show progress strip
        try:
            strip = self.query_one("#progress-strip")
            strip.add_class("visible")
            self.query_one("#progress-url", Static).update(f" {url}")
        except Exception:
            pass

        try:
            async for progress in self.pipeline.run(url):
                # Update progress strip
                try:
                    self.query_one("#progress-msg", Static).update(
                        f" [{progress.stage.upper()}] {progress.message}"
                    )
                    self.query_one("#progress-bar", ProgressBar).progress = progress.percent
                except Exception:
                    pass

                if progress.stage == "complete":
                    await self._on_analysis_complete(url, progress.message)
                elif progress.stage == "error":
                    self._append_chat("error", progress.message)

        except asyncio.CancelledError:
            self._append_chat("system", f"Analysis cancelled.")
        except Exception as e:
            self._append_chat("error", str(e))
        finally:
            self._active_tasks.pop(url, None)
            try:
                self.query_one("#progress-strip").remove_class("visible")
            except Exception:
                pass
            self._refresh_status()

    async def _on_analysis_complete(self, url: str, message: str) -> None:
        repo_name = url.rstrip("/").split("/")[-1]
        self.active_repo = repo_name
        self.mode = "QUERY"

        # Pull framework / language info from DB for sidebar
        try:
            from sqlmodel import select, Session
            from gitreverse.models import Framework, File, Repository
            with self.db.get_session() as session:
                repo_row = session.exec(
                    select(Repository).where(Repository.url == url)
                ).first()

                frameworks = []
                languages = []
                stats = {}

                if repo_row:
                    fws = session.exec(select(Framework).where(Framework.repository_id == repo_row.id)).all()
                    frameworks = [f.name + (f" {f.version}" if f.version else "") for f in fws]

                    files = session.exec(select(File).where(File.repository_id == repo_row.id)).all()
                    lang_counts: dict[str, int] = {}
                    for f in files:
                        lang_counts[f.language] = lang_counts.get(f.language, 0) + 1
                    languages = [f"{lang} ({cnt})" for lang, cnt in sorted(lang_counts.items(), key=lambda x: -x[1])]
                    stats = {
                        "Files": str(len(files)),
                        "Commit": repo_row.commit_hash[:8] if repo_row.commit_hash else "—",
                    }

            self.query_one("#sidebar", Sidebar).update_repo(
                name=repo_name,
                frameworks=frameworks,
                languages=languages,
                stats=stats,
            )
        except Exception as e:
            logger.warning(f"Sidebar update failed: {e}")

        self._append_chat(
            "result",
            f"## ✅ {repo_name} — Analysis Complete\n\n"
            f"{message}\n\n"
            f"The input box is now in **QUERY** mode. Ask anything about this repository."
        )

    # ── Query Handler ─────────────────────────────────────────────────────────

    async def _handle_query(self, query: str) -> None:
        if not self.active_repo:
            self._append_chat("system", "⚠ No repository analyzed yet. Paste a GitHub URL first.")
            return

        self._append_chat("user", query)
        self._append_chat("system", "_Querying knowledge graph…_")

        # Query the DB for relevant data
        loop = asyncio.get_event_loop()
        answer = await loop.run_in_executor(None, lambda: self._query_db(query))
        self._append_chat("result", answer)

    def _query_db(self, query: str) -> str:
        """Simple evidence-backed query router over SQLite."""
        q = query.lower()
        try:
            from sqlmodel import select, Session
            from gitreverse.models import Framework, Dependency, File, Repository

            with self.db.get_session() as session:
                repo_row = session.exec(
                    select(Repository).where(Repository.url.contains(self.active_repo))
                ).first()
                if not repo_row:
                    return f"No analysis data found for `{self.active_repo}`."

                rid = repo_row.id

                if any(w in q for w in ("framework", "stack", "library", "use", "built with")):
                    fws = session.exec(select(Framework).where(Framework.repository_id == rid)).all()
                    if not fws:
                        return "No frameworks detected in this repository."
                    lines = [f"## Detected Frameworks\n"]
                    for fw in fws:
                        ev = fw.evidence or {}
                        src = next(iter(ev.values()), "detected via analysis") if ev else "—"
                        lines.append(f"**{fw.name}** {fw.version or ''}\n- Evidence: `{src}`\n")
                    return "\n".join(lines)

                elif any(w in q for w in ("depend", "package", "npm", "pip", "cargo")):
                    deps = session.exec(select(Dependency).where(Dependency.repository_id == rid)).all()
                    if not deps:
                        return "No dependencies found."
                    by_type: dict[str, list] = {}
                    for d in deps:
                        by_type.setdefault(d.type, []).append(d)
                    lines = [f"## Dependencies ({len(deps)} total)\n"]
                    for dtype, ds in by_type.items():
                        lines.append(f"### {dtype.title()} ({len(ds)})")
                        for d in ds[:15]:
                            lines.append(f"- `{d.package_name}` {d.version or ''}")
                        if len(ds) > 15:
                            lines.append(f"- … and {len(ds)-15} more")
                        lines.append("")
                    return "\n".join(lines)

                elif any(w in q for w in ("file", "structure", "folder", "directory")):
                    files = session.exec(select(File).where(File.repository_id == rid)).all()
                    lang_counts: dict[str, int] = {}
                    for f in files:
                        lang_counts[f.language] = lang_counts.get(f.language, 0) + 1
                    lines = [f"## File Structure\n", f"**{len(files)} source files** detected\n"]
                    lines.append("### By Language")
                    for lang, cnt in sorted(lang_counts.items(), key=lambda x: -x[1]):
                        bar = "█" * min(cnt, 20)
                        lines.append(f"- `{lang}`: {cnt} files {bar}")
                    sample = [f.path for f in files[:10]]
                    lines.append(f"\n### Sample Files")
                    for p in sample:
                        lines.append(f"- `{p}`")
                    return "\n".join(lines)

                else:
                    fws = session.exec(select(Framework).where(Framework.repository_id == rid)).all()
                    deps = session.exec(select(Dependency).where(Dependency.repository_id == rid)).all()
                    files = session.exec(select(File).where(File.repository_id == rid)).all()
                    fw_names = ", ".join(f.name for f in fws) or "none detected"
                    return (
                        f"## Repository Summary: `{self.active_repo}`\n\n"
                        f"- **Frameworks**: {fw_names}\n"
                        f"- **Dependencies**: {len(deps)} packages\n"
                        f"- **Source Files**: {len(files)}\n"
                        f"- **Commit**: `{repo_row.commit_hash[:8]}`\n\n"
                        f"_Ask about frameworks, dependencies, or file structure for details._"
                    )
        except Exception as e:
            logger.error(f"DB query error: {e}")
            return f"Query error: {e}"

    # ── Chat Helpers ─────────────────────────────────────────────────────────

    def _remove_empty_state(self) -> None:
        try:
            empty = self.query_one("#empty-state")
            empty.remove()
        except Exception:
            pass

    def _append_chat(self, kind: str, content: str) -> None:
        self._remove_empty_state()
        viewport = self.query_one("#chat-viewport", ScrollableContainer)

        if kind == "user":
            widget = Static(f"[bold #58a6ff]▶ {escape(content)}[/]", classes="chat-user")
        elif kind == "system":
            widget = Static(f"[#8b949e]{content}[/]", classes="chat-system")
        elif kind == "error":
            widget = Static(f"[red]✗ {escape(content)}[/]", classes="chat-error")
        else:  # result
            widget = Markdown(content, classes="chat-result")

        asyncio.get_event_loop().run_until_complete(viewport.mount(widget)) if not self._is_running else self.call_from_thread(viewport.mount, widget) if False else None

        # Non-async mount via app.call_later
        self.call_later(self._mount_widget, viewport, widget)

    async def _mount_widget(self, viewport, widget) -> None:
        await viewport.mount(widget)
        viewport.scroll_end(animate=False)

    @property
    def _is_running(self) -> bool:
        return False


def main() -> None:
    setup_logging()
    app = GitReverseApp()
    app.run()


if __name__ == "__main__":
    main()
