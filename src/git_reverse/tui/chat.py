"""
TUI Chat Widget.

Handles the interactive conversation loop, displays streaming markdown responses,
and updates SQLite message history and token usage tracking.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual import on, work
from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.widgets import Input, Markdown, Static

from git_reverse.ai.client import OpenRouterClient
from git_reverse.ai.context import ContextCompiler
from git_reverse.ai.prompts import _SYSTEM_PROMPT, _USER_PROMPT_TEMPLATE
from git_reverse.ai.usage import UsageTracker
from git_reverse.core.logging import get_logger
from git_reverse.storage.database import MessageDAO

if TYPE_CHECKING:
    from git_reverse.storage.database import Database

log = get_logger(__name__)


class ChatArea(Markdown):
    """Renders the formatted markdown log of the session chat history."""
    DEFAULT_CSS = """
    ChatArea {
        height: 1fr;
        padding: 1 2;
        overflow-y: auto;
        border: solid $primary-darken-2;
    }
    """


class ChatPane(Vertical):
    """The complete query interaction interface widget."""

    DEFAULT_CSS = """
    ChatPane {
        height: 1fr;
        padding: 1;
    }
    #chat-input-box {
        margin-top: 1;
        height: auto;
    }
    """

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
        self._chat_history_markdown = ""

    def compose(self) -> ComposeResult:
        yield ChatArea(id="chat-area")
        with Container(id="chat-input-box"):
            yield Input(placeholder="Ask a question about this repository...", id="chat-input")

    def set_session(self, session_id: str, repo_id: str | None) -> None:
        """Switch the current chat context to a new session."""
        self.session_id = session_id
        self.repo_id = repo_id
        self._chat_history_markdown = ""
        self.query_one("#chat-area", ChatArea).update("")
        self._load_message_history()

    @work(exclusive=True)
    async def _load_message_history(self) -> None:
        """Load past message logs for this session from SQLite."""
        if not self.session_id:
            return
        
        try:
            history = await self._message_dao.get_history(self.session_id)
            md_list = []
            for msg in history:
                role_label = "**User**" if msg.role == "user" else "**Assistant**"
                md_list.append(f"{role_label}:\n\n{msg.content}\n\n---")
            self._chat_history_markdown = "\n".join(md_list)
            self.query_one("#chat-area", ChatArea).update(self._chat_history_markdown)
        except Exception as exc:  # noqa: BLE001
            log.error("chat_history_load_failed", error=str(exc))

    @on(Input.Submitted, "#chat-input")
    async def on_query_submitted(self, event: Input.Submitted) -> None:
        """Handle query input submission from user."""
        query = event.value.strip()
        if not query or not self.session_id:
            return
            
        event.input.clear()
        
        # Disable input while processing
        event.input.disabled = True
        
        # Display user question
        self._chat_history_markdown += f"\n\n**User**:\n\n{query}\n\n---\n\n**Assistant**:\n\n"
        chat_area = self.query_one("#chat-area", ChatArea)
        chat_area.update(self._chat_history_markdown)
        
        # Spawn async LLM worker
        self._run_query_worker(query, event.input)

    @work(exclusive=True)
    async def _run_query_worker(self, query: str, input_widget: Input) -> None:
        """Asynchronously compiles context, queries OpenRouter, and updates database."""
        session_id = self.session_id
        repo_id = self.repo_id
        
        if not session_id:
            input_widget.disabled = False
            return

        import time
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
            for h in history[:-1]:  # exclude the query we just added to prevent duplicate
                messages.append({"role": h.role, "content": h.content})

            # Append current query wrapped with context
            prompt = _USER_PROMPT_TEMPLATE.format(context_str=context_str, query=query)
            messages.append({"role": "user", "content": prompt})

            # 4. Stream response
            chat_area = self.query_one("#chat-area", ChatArea)
            response_content = ""
            prompt_tokens = 0
            completion_tokens = 0

            async for chunk, p_tokens, c_tokens in self._client.stream_completion(
                messages, model=self._default_model
            ):
                response_content += chunk
                # Update text in TUI
                chat_area.update(self._chat_history_markdown + response_content)
                if p_tokens > 0:
                    prompt_tokens = p_tokens
                if c_tokens > 0:
                    completion_tokens = c_tokens

            # Append completed markdown separator
            self._chat_history_markdown += f"{response_content}\n\n---"
            chat_area.update(self._chat_history_markdown)

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

        except Exception as exc:  # noqa: BLE001
            log.error("query_execution_failed", error=str(exc))
            self._chat_history_markdown += f"\n\n*Error: Failed to fetch response. {exc}*\n\n---"
            self.query_one("#chat-area", ChatArea).update(self._chat_history_markdown)
        finally:
            input_widget.disabled = False
            input_widget.focus()
