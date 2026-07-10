# ruff: noqa: E501
"""
TUI Chat Widget.

Handles the interactive conversation loop, displays streaming markdown responses,
and updates SQLite message history and token usage tracking.
"""

from __future__ import annotations

import subprocess
import sys
import time
from typing import TYPE_CHECKING

from textual import on, work
from textual.app import ComposeResult
from textual.containers import Container, ScrollableContainer, Vertical
from textual.message import Message
from textual.widgets import Button, Input, Label, Markdown

from git_reverse.ai.client import OpenRouterClient
from git_reverse.ai.context import ContextCompiler
from git_reverse.ai.prompts import _SYSTEM_PROMPT, _USER_PROMPT_TEMPLATE
from git_reverse.ai.usage import UsageTracker
from git_reverse.core.logging import get_logger
from git_reverse.storage.database import MessageDAO

if TYPE_CHECKING:
    from git_reverse.storage.database import Database

log = get_logger(__name__)


def copy_to_clipboard(text: str) -> bool:
    """Copy string securely to clipboard across Windows, macOS, and Linux."""
    try:
        if sys.platform == "win32":
            process = subprocess.Popen(['clip'], stdin=subprocess.PIPE, text=True, encoding='utf-8')
            process.communicate(input=text)
            return True
        elif sys.platform == "darwin":
            process = subprocess.Popen(['pbcopy'], stdin=subprocess.PIPE, text=True, encoding='utf-8')
            process.communicate(input=text)
            return True
        else:
            for cmd in ['xclip -selection clipboard', 'xsel -ib']:
                try:
                    parts = cmd.split()
                    process = subprocess.Popen(parts, stdin=subprocess.PIPE, text=True, encoding='utf-8')
                    process.communicate(input=text)
                    return True
                except FileNotFoundError:
                    continue
    except Exception as exc:
        log.error("clipboard_copy_failed", error=str(exc))
    return False


class UserMessageWidget(Container):
    """Render a user message block with clear visual distinction."""

    def __init__(self, content: str) -> None:
        super().__init__()
        self.content = content

    def compose(self) -> ComposeResult:
        yield Label("User", classes="user-label")
        yield Markdown(self.content)


class AssistantMessageWidget(Container):
    """Render assistant markdown response with an inline clipboard copy button."""

    def __init__(self, content: str = "") -> None:
        super().__init__()
        self.content = content

    def compose(self) -> ComposeResult:
        with Container(classes="assistant-header"):
            yield Label("Assistant", classes="assistant-label")
            yield Button("Copy", classes="copy-btn")
        yield Markdown(self.content, id="assistant-md")

    def update_content(self, text: str) -> None:
        self.content = text
        self.query_one("#assistant-md", Markdown).update(self.content)

    @on(Button.Pressed, ".copy-btn")
    def on_copy_pressed(self) -> None:
        if copy_to_clipboard(self.content):
            if hasattr(self.app, "set_status_message"):
                self.app.set_status_message("Copied to system clipboard!")
        else:
            if hasattr(self.app, "set_status_message"):
                self.app.set_status_message("Failed to copy text.")


class ChatInput(Input):
    """Custom input to intercept Tab key events to cycle modes."""

    class TabPressed(Message):
        """Dispatched when Tab is pressed in the input field."""
        def __init__(self, control: ChatInput) -> None:
            super().__init__()
            self._control = control

        @property
        def control(self) -> ChatInput:
            return self._control

    def key_tab(self) -> None:
        self.post_message(self.TabPressed(self))


class ChatArea(ScrollableContainer):
    """Renders the scrollable log of individual chat messages."""


class ChatPane(Vertical):
    """The query interaction interface widget."""

    def __init__(self, db: Database, api_key: str, default_model: str) -> None:
        super().__init__()
        self._db = db
        self._api_key = api_key
        self._default_model = default_model

        self._message_dao = MessageDAO(db)
        self._compiler = ContextCompiler(db)
        self._tracker = UsageTracker(db)
        self._client = OpenRouterClient(api_key, default_model)

        self.session_id: str | None = None
        self.repo_id: str | None = None
        self._current_mode = "explore"

    def compose(self) -> ComposeResult:
        yield ChatArea(id="chat-area")
        with Container(id="chat-input-box"):
            yield Label("Mode: explore  (Press Tab to cycle)", id="chat-mode-label")
            yield ChatInput(placeholder="Ask a question about this repository...", id="chat-input")

    def set_session(self, session_id: str, repo_id: str | None) -> None:
        """Switch the current chat context to a new session."""
        self.session_id = session_id
        self.repo_id = repo_id

        chat_area = self.query_one("#chat-area", ChatArea)
        chat_area.remove_children()

        self._load_message_history()

    @work(exclusive=True)
    async def _load_message_history(self) -> None:
        """Load past message logs for this session from SQLite."""
        if not self.session_id:
            return

        try:
            history = await self._message_dao.get_history(self.session_id)
            chat_area = self.query_one("#chat-area", ChatArea)
            for msg in history:
                if msg.role == "user":
                    chat_area.mount(UserMessageWidget(msg.content))
                else:
                    chat_area.mount(AssistantMessageWidget(msg.content))

            chat_area.scroll_end(animate=False)
        except Exception as exc:
            log.error("chat_history_load_failed", error=str(exc))

    @on(ChatInput.TabPressed, "#chat-input")
    def on_tab_pressed(self) -> None:
        """Cycle active session mode."""
        self._cycle_mode()

    @on(Input.Changed, "#chat-input")
    def on_input_changed(self, event: Input.Changed) -> None:
        """Show slash commands tooltip when typing /."""
        val = event.value.strip()
        if val.startswith("/"):
            self.query_one("#chat-mode-label", Label).update(
                "Commands: /settings, /compact, /deep_dive, /section"
            )
        else:
            self.query_one("#chat-mode-label", Label).update(
                f"Mode: {self._current_mode.replace('_', ' ')}  (Press Tab to cycle)"
            )

    @on(Input.Submitted, "#chat-input")
    async def on_query_submitted(self, event: Input.Submitted) -> None:
        """Handle query input submission from user."""
        query = event.value.strip()
        if not query or not self.session_id:
            return

        event.input.clear()

        # Parse slash commands
        if query.startswith("/"):
            await self._handle_slash_command(query, event.input)
            return

        await self._submit_query(query, event.input)

    def submit_query(self, query: str) -> None:
        """Programmatically submit a query to the chat."""
        if not self.session_id:
            return
        input_widget = self.query_one("#chat-input", ChatInput)
        self.run_worker(self._submit_query(query, input_widget))

    async def _submit_query(self, query: str, input_widget: ChatInput) -> None:
        input_widget.disabled = True

        chat_area = self.query_one("#chat-area", ChatArea)
        chat_area.mount(UserMessageWidget(query))

        assistant_widget = AssistantMessageWidget("")
        chat_area.mount(assistant_widget)
        chat_area.scroll_end()

        self._run_query_worker(query, assistant_widget, input_widget)

    @work(exclusive=True)
    async def _run_query_worker(
        self, query: str, assistant_widget: AssistantMessageWidget, input_widget: ChatInput
    ) -> None:
        """Asynchronously compiles context, queries OpenRouter, and updates database."""
        session_id = self.session_id
        repo_id = self.repo_id

        if not session_id:
            input_widget.disabled = False
            return

        start_time = time.monotonic()

        try:
            # 1. Save user query to DB
            await self._message_dao.append(session_id=session_id, role="user", content=query)

            # 2. Compile ranked repository context
            context_str = ""
            if repo_id:
                context_str = await self._compiler.compile_context(repo_id, query)

            # 3. Construct messages payload
            messages = [{"role": "system", "content": _SYSTEM_PROMPT}]

            # Fetch past logs for short-term history context (last 6 messages)
            history = await self._message_dao.get_history(session_id, limit=6)
            for h in history[:-1]:  # exclude current query
                messages.append({"role": h.role, "content": h.content})

            # Append current query wrapped with context
            prompt = _USER_PROMPT_TEMPLATE.format(context_str=context_str, query=query)
            messages.append({"role": "user", "content": prompt})

            # 4. Stream response
            response_content = ""
            prompt_tokens = 0
            completion_tokens = 0

            async for chunk, p_tokens, c_tokens in self._client.stream_completion(
                messages, model=self._default_model
            ):
                response_content += chunk
                assistant_widget.update_content(response_content)
                self.query_one("#chat-area", ChatArea).scroll_end(animate=False)

                if p_tokens > 0:
                    prompt_tokens = p_tokens
                if c_tokens > 0:
                    completion_tokens = c_tokens

            # 5. Save assistant response to DB
            await self._message_dao.append(
                session_id=session_id,
                role="assistant",
                content=response_content,
                model=self._default_model,
                tokens_used=prompt_tokens + completion_tokens,
            )

            # 6. Log usage cost
            latency = int((time.monotonic() - start_time) * 1000)
            await self._tracker.log_request(
                session_id=session_id,
                model=self._default_model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                latency_ms=latency,
            )

        except Exception as exc:
            log.error("query_execution_failed", error=str(exc))
            assistant_widget.update_content(f"\n\n*Error: Failed to fetch response. {exc}*")
        finally:
            input_widget.disabled = False
            input_widget.focus()

    def _cycle_mode(self) -> None:
        modes = ["explore", "prompt_recreation", "non-technical", "intermediate", "developer"]
        try:
            idx = modes.index(self._current_mode)
            next_mode = modes[(idx + 1) % len(modes)]
        except ValueError:
            next_mode = "explore"

        self._current_mode = next_mode
        self.query_one("#chat-mode-label", Label).update(
            f"Mode: {next_mode.replace('_', ' ')}  (Press Tab to cycle)"
        )
        self.run_worker(self._update_session_mode(next_mode))

    async def _update_session_mode(self, mode: str) -> None:
        if self.session_id:
            try:
                from git_reverse.storage.database import SessionDAO
                session_dao = SessionDAO(self._db)
                await session_dao.update_mode(self.session_id, mode)
                if hasattr(self.app, "set_status_message"):
                    self.app.set_status_message(f"Switched mode to {mode.replace('_', ' ')}")
            except Exception as exc:
                log.error("failed_to_update_mode", error=str(exc))

    async def _handle_slash_command(self, cmd_str: str, input_widget: ChatInput) -> None:
        parts = cmd_str.split(maxsplit=1)
        cmd = parts[0].lower()

        chat_area = self.query_one("#chat-area", ChatArea)

        if cmd == "/settings":
            self.app.action_switch_model()

        elif cmd in ("/compact", "/summarize"):
            chat_area.mount(UserMessageWidget(f"Command: {cmd_str}"))
            summary_widget = AssistantMessageWidget("Generating summary...")
            chat_area.mount(summary_widget)
            chat_area.scroll_end()
            self._run_query_worker(
                "Please generate a compact summary of this conversation.",
                summary_widget,
                input_widget
            )

        elif cmd == "/deep_dive":
            chat_area.mount(UserMessageWidget(f"Command: {cmd_str}"))
            deep_widget = AssistantMessageWidget("Initiating deep architecture scan...")
            chat_area.mount(deep_widget)
            chat_area.scroll_end()
            self._run_query_worker(
                "Generate a highly structured blueprint prompt detailing the folder structure, AST architecture, schemas, and logic of this codebase so that a developer can recreate it from scratch.",
                deep_widget,
                input_widget
            )

        elif cmd == "/section":
            chat_area.mount(UserMessageWidget(f"Command: {cmd_str}"))
            section_widget = AssistantMessageWidget("Fetching session histories...")
            chat_area.mount(section_widget)
            chat_area.scroll_end()

            try:
                from git_reverse.storage.database import SessionDAO
                session_dao = SessionDAO(self._db)
                sessions = await session_dao.list_recent(limit=10)
                md = "### Recent Sessions:\n\n"
                for s in sessions:
                    repo_str = f"Repo: {s.repo_id}" if s.repo_id else "Global"
                    summary_str = f" - *{s.summary}*" if s.summary else ""
                    md += f"- **{s.id}** ({s.mode}) | {repo_str}{summary_str}\n"
                section_widget.update_content(md)
            except Exception as e:
                section_widget.update_content(f"Error: {e}")

        else:
            chat_area.mount(UserMessageWidget(f"Command: {cmd_str}"))
            err_widget = AssistantMessageWidget(
                f"Unknown command: `{cmd}`. Available: `/settings`, `/compact`, `/deep_dive`, `/section`"
            )
            chat_area.mount(err_widget)
            chat_area.scroll_end()
