from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QPlainTextEdit,
    QFrame, QApplication, QSizePolicy, QComboBox, QProgressBar
)
from PySide6.QtCore import Qt, QTimer, QThread, Signal
from app.services.secrets import SecretsManager
from app.services.llm_client import LLMClient
from app.services.database import DatabaseManager


class ChatWorker(QThread):
    """Background thread for evidence retrieval and streaming LLM chat responses (INV2 — main thread never blocks)."""

    thinking_step = Signal(int, str)  # (gen_id, msg)
    token_received = Signal(int, str) # (gen_id, token)
    finished = Signal(int, int)       # (gen_id, token_count)
    failed = Signal(int, str)         # (gen_id, error_msg)

    def __init__(self, api_key: str, base_url: str, model_id: str,
                 system_ctx: str, user_msg: str, history: list,
                 gen_id: int = 0,
                 ai_mode: str = "General", session_id: int = None,
                 parent=None):
        super().__init__(parent)
        self.api_key = api_key
        self.base_url = base_url
        self.model_id = model_id
        self.system_ctx = system_ctx
        self.user_msg = user_msg
        self.history = history
        self.gen_id = gen_id
        self.ai_mode = ai_mode
        self.session_id = session_id
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        try:
            # Step 1: Thinking — FTS5 Evidence Retrieval (§37–39)
            self.thinking_step.emit(self.gen_id, "Searching Knowledge Base via FTS5 index...")
            db = DatabaseManager()
            fts_matches = db.search_fts(self.user_msg)

            evidence_block = ""
            if fts_matches:
                self.thinking_step.emit(self.gen_id, f"Retrieved {len(fts_matches[:4])} evidence snippets from FTS5 index...")
                evidence_items = []
                for idx, match in enumerate(fts_matches[:4], 1):
                    raw_syms = match.get("raw_symbol_matches") or []
                    raw_section = ""
                    if raw_syms:
                        raw_section = "  Raw Source AST Symbols:\n    - " + "\n    - ".join(raw_syms) + "\n"
                    evidence_items.append(
                        f"  [Evidence #{idx} — Repo: {match.get('repo_name', 'Unknown')}]\n"
                        f"{raw_section}"
                        f"  Prompt Summary Excerpt: {match.get('prompt_snippet', '')[:300]}"
                    )
                evidence_block = "\n\nRETRIEVED CODE EVIDENCE (Cite [Evidence #N] and exact line numbers/symbols when answering):\n" + "\n\n".join(evidence_items)

            full_system_ctx = self.system_ctx + evidence_block

            # Step 2: Thinking — Connecting to AI Gateway
            self.thinking_step.emit(self.gen_id, f"Connecting to AI gateway ({self.model_id})...")

            client = LLMClient(api_key=self.api_key, base_url=self.base_url, model_id=self.model_id)

            token_count = 0
            def on_token(tokens: int):
                nonlocal token_count
                token_count = tokens

            for token in client.stream_chat(
                full_system_ctx,
                self.user_msg,
                self.history,
                ai_mode=self.ai_mode,
                token_callback=on_token,
            ):
                if self._cancelled:
                    break
                self.token_received.emit(self.gen_id, token)

            self.finished.emit(self.gen_id, token_count)

        except Exception as e:
            self.failed.emit(self.gen_id, str(e))


CHAT_SYSTEM_CONTEXT = (
    "You are an evidence-grounded technical assistant for Git Reverse. "
    "You analyze repository architectures, code structures, and dependency trees. "
    "Be concise, precise, and cite provided evidence explicitly when applicable."
)


class ChatView(QWidget):
    """KB Chat Console — evidence-backed RAG streaming chat with AI thinking state indicators (§37–39, §40, §58)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._history = []
        self._worker: ChatWorker = None
        self._active_session: dict = None
        self._current_gen_id = 0
        self._current_response_buffer = ""
        self.db_mgr = DatabaseManager()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        # ── Header ──────────────────────────────────────────────────────────
        top_bar = QFrame()
        top_bar.setProperty("class", "g-pane")
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(14, 10, 14, 10)
        top_layout.setSpacing(10)

        title = QLabel("KB Chat Console")
        title.setStyleSheet("font-size: 14px; font-weight: 600;")

        self.combo_session = QComboBox()
        self.combo_session.setMinimumWidth(220)
        self.combo_session.currentIndexChanged.connect(self.on_session_changed)
        self.refresh_session_dropdown()

        mode_lbl = QLabel("Mode:")
        mode_lbl.setStyleSheet("font-size: 11px; font-weight: 600; color: #71717a;")

        self._ai_mode_combo = QComboBox()
        self._ai_mode_combo.addItems(["General", "Explain", "Architect", "Developer", "Documentation"])
        self._ai_mode_combo.setMinimumHeight(30)
        self._ai_mode_combo.setFixedWidth(120)

        self.lbl_model = QLabel("No model configured")
        self.lbl_model.setStyleSheet(
            "font-size: 11px; font-weight: 600; color: #2563eb; "
            "background-color: rgba(37, 99, 235, 0.1); padding: 3px 10px; border-radius: 10px; "
            "border: 1px solid rgba(37, 99, 235, 0.3);"
        )
        self.refresh_model_label()

        btn_clear = QPushButton("Clear Chat")
        btn_clear.setProperty("class", "g-btn-ghost")
        btn_clear.clicked.connect(self.on_clear_clicked)

        top_layout.addWidget(title)
        top_layout.addWidget(self.combo_session)
        top_layout.addStretch()
        top_layout.addWidget(mode_lbl)
        top_layout.addWidget(self._ai_mode_combo)
        top_layout.addWidget(self.lbl_model)
        top_layout.addWidget(btn_clear)
        layout.addWidget(top_bar)

        # Async State Contract Widget for Chat Operations
        from app.views.components import AsyncStateWidget
        self.state_widget = AsyncStateWidget()
        self.state_widget.retry_requested.connect(self.on_retry_clicked)
        layout.addWidget(self.state_widget)

        # ── AI Thinking State Indicator Bar (§37–39) ───────────────────────
        self.thinking_bar = QFrame()
        self.thinking_bar.setStyleSheet(
            "QFrame { background: rgba(37, 99, 235, 0.08); border: 1px solid rgba(37, 99, 235, 0.2); border-radius: 6px; padding: 4px 10px; }"
        )
        t_layout = QHBoxLayout(self.thinking_bar)
        t_layout.setContentsMargins(8, 4, 8, 4)
        t_layout.setSpacing(8)

        self.lbl_thinking = QLabel("AI Thinking State: Idle")
        self.lbl_thinking.setStyleSheet("font-size: 11px; font-weight: 600; color: #2563eb;")

        self.thinking_progress = QProgressBar()
        self.thinking_progress.setRange(0, 0)
        self.thinking_progress.setFixedHeight(3)
        self.thinking_progress.setTextVisible(False)

        t_layout.addWidget(self.lbl_thinking)
        t_layout.addWidget(self.thinking_progress, 1)
        self.thinking_bar.hide()
        layout.addWidget(self.thinking_bar)

        # ── Chat Stream ──────────────────────────────────────────────────────
        self.chat_stream = QPlainTextEdit()
        self.chat_stream.setReadOnly(True)
        self.chat_stream.setPlaceholderText(
            "Chat with Git Reverse AI (Evidence-backed RAG).\n\n"
            "Ask questions about analyzed codebases. Answers cite exact FTS5 evidence snippets."
        )
        self.chat_stream.setStyleSheet("font-family: 'Geist Mono', 'Consolas', monospace; font-size: 12px; line-height: 1.5;")
        layout.addWidget(self.chat_stream, 1)

        # ── Quick Prompt Chips ───────────────────────────────────────────────
        chips_layout = QHBoxLayout()
        chips_layout.setSpacing(6)
        chips = [
            ("Explain Entrypoints", "Explain the main entrypoints and initialization flow in an analyzed repository."),
            ("Dependency Summary", "Summarize all detected core frameworks, dependencies, and manifest declarations."),
            ("Security & License", "Summarize the detected license, copyleft obligations, and security recommendations."),
            ("Architecture Pattern", "Explain the architecture pattern detected and how to replicate its structure."),
        ]
        for label, prompt in chips:
            btn = QPushButton(label)
            btn.setProperty("class", "g-btn-chip")
            btn.clicked.connect(lambda checked, p=prompt: self.send_prompt(p))
            chips_layout.addWidget(btn)
        chips_layout.addStretch()
        layout.addLayout(chips_layout)

        # ── Input Panel & Pre-Send Token Cost Preview (§40, §64) ────────────
        input_pane = QFrame()
        input_pane.setProperty("class", "g-pane")
        input_vlayout = QVBoxLayout(input_pane)
        input_vlayout.setContentsMargins(12, 10, 12, 10)
        input_vlayout.setSpacing(6)

        input_hlayout = QHBoxLayout()
        input_hlayout.setSpacing(8)

        self.input_edit = QPlainTextEdit()
        self.input_edit.setFixedHeight(52)
        self.input_edit.setPlaceholderText("Ask a question about codebase architecture, dependencies, or licenses…")
        self.input_edit.textChanged.connect(self.on_input_text_changed)

        self.btn_send = QPushButton("Send")
        self.btn_send.setProperty("class", "g-btn-solid")
        self.btn_send.setCursor(Qt.PointingHandCursor)
        self.btn_send.setFixedHeight(52)
        self.btn_send.clicked.connect(self.on_send_clicked)

        input_hlayout.addWidget(self.input_edit, 1)
        input_hlayout.addWidget(self.btn_send)
        input_vlayout.addLayout(input_hlayout)

        # Token cost preview & Retry button bar
        token_row = QHBoxLayout()
        self.lbl_token_est = QLabel("Est. Input: ~0 tokens")
        self.lbl_token_est.setStyleSheet("font-size: 10px; font-family: monospace; color: #71717a;")
        token_row.addWidget(self.lbl_token_est)

        self.btn_retry = QPushButton("Retry Request")
        self.btn_retry.setProperty("class", "g-btn-ghost")
        self.btn_retry.setStyleSheet("font-size: 10px; color: #ef4444; border: 1px solid rgba(239, 68, 68, 0.4); padding: 2px 8px;")
        self.btn_retry.hide()
        self.btn_retry.clicked.connect(self.on_retry_clicked)
        token_row.addStretch()
        token_row.addWidget(self.btn_retry)

        input_vlayout.addLayout(token_row)

        layout.addWidget(input_pane)

    def refresh_session_dropdown(self):
        self.combo_session.blockSignals(True)
        self.combo_session.clear()
        self.combo_session.addItem("Global Assistant (All Sessions)", None)
        sessions = self.db_mgr.get_recent_sessions_summary()
        for s in sessions:
            self.combo_session.addItem(f"Repo: {s['repo_name']} ({s['language']})", s)
        self.combo_session.blockSignals(False)

    def on_session_changed(self, idx: int):
        data = self.combo_session.currentData()
        self._active_session = data
        if data:
            self.chat_stream.appendPlainText(f"\n[System Context: Switched to repository '{data['repo_name']}']\n")
        else:
            self.chat_stream.appendPlainText("\n[System Context: Switched to Global AI Assistant]\n")

    def select_session_by_id(self, session_id: int):
        self.refresh_session_dropdown()
        for i in range(self.combo_session.count()):
            data = self.combo_session.itemData(i)
            if data and data.get("id") == session_id:
                self.combo_session.setCurrentIndex(i)
                return

    def refresh_model_label(self):
        config = SecretsManager.load_config()
        model = config.get("model_id", "gpt-4o")
        provider = config.get("provider_preset", "OpenAI")
        self.lbl_model.setText(f"{provider} / {model}")

    def on_clear_clicked(self):
        self.chat_stream.clear()
        self._history = []
        self.btn_retry.hide()

    def on_input_text_changed(self):
        """Pre-send Token Cost Estimation with threshold warning (§40, §64)."""
        text = self.input_edit.toPlainText().strip()
        words = len(text.split())
        est_tokens = int(words * 1.3)
        if est_tokens > 4000:
            self.lbl_token_est.setText(f"Est. Input: ~{est_tokens} tokens (Warning: High token count!)")
            self.lbl_token_est.setStyleSheet("font-size: 10px; font-family: monospace; color: #ef4444; font-weight: 600;")
        else:
            self.lbl_token_est.setText(f"Est. Input: ~{est_tokens} tokens")
            self.lbl_token_est.setStyleSheet("font-size: 10px; font-family: monospace; color: #71717a;")

    def send_prompt(self, text: str):
        self.input_edit.setPlainText(text)
        self.on_send_clicked()

    def on_retry_clicked(self):
        self.btn_retry.hide()
        if self._history and self._history[-1].get("role") == "user":
            last_msg = self._history[-1].get("content", "")
            self.input_edit.setPlainText(last_msg)
            self._history.pop()  # Remove pending user entry before re-sending
            self.on_send_clicked()

    def _hide_thinking_bar(self):
        from PySide6.QtCore import QDateTime
        elapsed = QDateTime.currentMSecsSinceEpoch() - getattr(self, "_thinking_start_time", 0)
        if elapsed < 400:
            QTimer.singleShot(400 - elapsed, lambda: self.thinking_bar.hide())
        else:
            self.thinking_bar.hide()

    def on_send_clicked(self):
        text = self.input_edit.toPlainText().strip()
        if not text:
            return

        api_key = SecretsManager.get_api_key()
        config = SecretsManager.load_config()

        if not api_key:
            self.chat_stream.appendPlainText(
                "\n[System] No API Key configured. Go to Settings and paste your BYOK key."
            )
            return

        words = len(text.split())
        est_tokens = int(words * 1.3)
        if est_tokens > 8000:
            self.chat_stream.appendPlainText(
                f"\n[System Warning] Input token estimate (~{est_tokens} tokens) exceeds standard context limit guardrail (8,000 tokens)."
            )

        # Spending Protection Check (§64)
        daily_limit = float(config.get("daily_spend_limit_usd", 0.0) or 0.0)
        monthly_limit = float(config.get("monthly_spend_limit_usd", 0.0) or 0.0)
        limit_action = config.get("spend_limit_action", "warn")

        if daily_limit > 0 or monthly_limit > 0:
            summary = self.db_mgr.get_spending_summary()
            today_cost = summary.get("today_cost_usd", 0.0)
            month_cost = summary.get("month_cost_usd", 0.0)

            exceeded = []
            if daily_limit > 0 and today_cost >= daily_limit:
                exceeded.append(f"Daily limit (${today_cost:.2f} / ${daily_limit:.2f})")
            if monthly_limit > 0 and month_cost >= monthly_limit:
                exceeded.append(f"Monthly limit (${month_cost:.2f} / ${monthly_limit:.2f})")

            if exceeded:
                msg = f"\n[Spending Protection] " + ", ".join(exceeded) + " reached."
                if limit_action == "block":
                    self.chat_stream.appendPlainText(msg + " Block action enabled — new LLM queries are blocked.\n")
                    return
                else:
                    self.chat_stream.appendPlainText(msg + " Warning action enabled.\n")

        self.input_edit.clear()
        self.btn_send.setEnabled(False)
        self.btn_send.setText("…")
        self.btn_retry.hide()

        self.chat_stream.appendHtml(f"<br><b style='color: #2563eb; font-size: 12px;'>You:</b> {text}<br>")
        self.chat_stream.appendHtml("<b style='color: #10b981; font-size: 12px;'>Assistant:</b> ")

        self._history.append({"role": "user", "content": text})
        self._current_response_buffer = ""
        self._current_gen_id += 1
        current_gen_id = self._current_gen_id

        if self._worker and self._worker.isRunning():
            try:
                self._worker.thinking_step.disconnect()
                self._worker.token_received.disconnect()
                self._worker.finished.disconnect()
                self._worker.failed.disconnect()
            except Exception:
                pass
            self._worker.cancel()
            self._worker.quit()
            if not self._worker.wait(1000):
                self._worker.terminate()
                self._worker.wait(500)

        base_url = config.get("base_url", "https://api.openai.com/v1")
        model_id = config.get("model_id", "gpt-4o").replace("[FREE] ", "")

        ai_mode_str = self._ai_mode_combo.currentText()
        from app.services.llm_client import AI_MODES
        base_system_prompt = AI_MODES.get(ai_mode_str, AI_MODES["General"])

        system_ctx = base_system_prompt
        if self._active_session:
            system_ctx += (
                f"\n\nACTIVE REPOSITORY CONTEXT:\n"
                f"- Repository Name: {self._active_session.get('repo_name')}\n"
                f"- Repository URL: {self._active_session.get('repo_url')}\n"
                f"- Primary Language: {self._active_session.get('language')}\n"
                f"- Source License: {self._active_session.get('source_license')}\n"
                f"- File Count: {self._active_session.get('file_count')}\n"
                f"- Recreation Prompt Excerpt:\n{self._active_session.get('generated_prompt', '')[:1000]}"
            )

        ai_mode_str = self._ai_mode_combo.currentText()
        session_id = self._active_session.get("id") if self._active_session else None

        from PySide6.QtCore import QDateTime
        self._thinking_start_time = QDateTime.currentMSecsSinceEpoch()
        self.lbl_thinking.setText("AI Thinking State: Searching Knowledge Base via FTS5 index...")
        self.thinking_bar.show()

        self._worker = ChatWorker(
            api_key=api_key,
            base_url=base_url,
            model_id=model_id,
            system_ctx=system_ctx,
            user_msg=text,
            history=self._history[:-1],
            gen_id=current_gen_id,
            ai_mode=ai_mode_str,
            session_id=session_id,
            parent=self,
        )
        self.state_widget.set_loading("Searching FTS5 evidence index & generating response...")
        self._worker.thinking_step.connect(self.on_thinking_step)
        self._worker.token_received.connect(self.on_chat_token)
        self._worker.finished.connect(self.on_chat_done)
        self._worker.failed.connect(self.on_chat_failed)
        self._worker.start()

    def on_thinking_step(self, gen_id: int, step_msg: str):
        if gen_id != self._current_gen_id:
            return
        self.lbl_thinking.setText(f"AI Thinking State: {step_msg}")
        self.state_widget.set_loading(step_msg)

    def on_chat_token(self, gen_id: int, token: str):
        if gen_id != self._current_gen_id:
            return
        self.lbl_thinking.setText("AI Thinking State: Streaming response...")
        self._current_response_buffer += token
        self.chat_stream.insertPlainText(token)
        sb = self.chat_stream.verticalScrollBar()
        sb.setValue(sb.maximum())

    def on_chat_done(self, gen_id: int, token_count: int):
        if gen_id != self._current_gen_id:
            return
        self.btn_send.setEnabled(True)
        self.btn_send.setText("Send")
        self._hide_thinking_bar()
        self.state_widget.set_success("Response complete")
        self.chat_stream.appendPlainText("\n")
        if self._current_response_buffer:
            self._history.append({"role": "assistant", "content": self._current_response_buffer})
            self._current_response_buffer = ""

        # Log token usage to SQLite SpendingLog
        if token_count > 0:
            est_cost = round((token_count / 1000.0) * 0.002, 6)
            self.db_mgr.log_token_usage(tokens=token_count, estimated_cost_usd=est_cost)

    def on_chat_failed(self, gen_id: int, err: str):
        if gen_id != self._current_gen_id:
            return
        self.btn_send.setEnabled(True)
        self.btn_send.setText("Send")
        self.btn_retry.show()
        self._hide_thinking_bar()
        self.state_widget.set_error(err)
        self.chat_stream.appendPlainText(f"\n[Error: {err}]\n")
