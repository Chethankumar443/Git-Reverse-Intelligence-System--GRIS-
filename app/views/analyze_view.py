from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QPlainTextEdit, QFrame, QSplitter, QProgressBar, QMessageBox, QApplication,
    QComboBox, QGridLayout
)
from PySide6.QtCore import Qt, QTimer, Signal
from app.viewmodels.analysis_vm import AnalysisViewModel


class AnalyzeView(QWidget):
    """Enterprise Desktop Workspace View: Repository Ingestion & Real-Time Prompt Streaming."""

    chat_requested = Signal(int)

    def __init__(self, analysis_vm: AnalysisViewModel, parent=None):
        super().__init__(parent)
        self.vm = analysis_vm
        self._current_session_id: int = None
        self.init_ui()
        self.bind_vm()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # ── Top Command Bar ─────────────────────────────────────────────────
        top_bar = QFrame()
        top_bar.setProperty("class", "g-pane")
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(16, 12, 16, 12)
        top_layout.setSpacing(12)

        url_label = QLabel("Repository URL")
        url_label.setStyleSheet("font-weight: 600; font-size: 13px;")

        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://github.com/owner/repository")
        self.url_input.setMinimumHeight(38)
        self.url_input.returnPressed.connect(self.on_ingest_clicked)

        self.ingest_btn = QPushButton("Ingest Repository")
        self.ingest_btn.setProperty("class", "g-btn-solid")
        self.ingest_btn.setCursor(Qt.PointingHandCursor)
        self.ingest_btn.setFixedHeight(38)
        self.ingest_btn.setMinimumWidth(140)
        self.ingest_btn.clicked.connect(self.on_ingest_clicked)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setProperty("class", "g-btn-ghost")
        self.cancel_btn.setFixedHeight(38)
        self.cancel_btn.hide()
        self.cancel_btn.clicked.connect(self.on_cancel_clicked)

        top_layout.addWidget(url_label)
        top_layout.addWidget(self.url_input, 1)
        top_layout.addWidget(self.ingest_btn)
        top_layout.addWidget(self.cancel_btn)
        layout.addWidget(top_bar)

        # Reusable Async State Contract Widget
        from app.views.components import AsyncStateWidget
        self.state_widget = AsyncStateWidget()
        self.state_widget.retry_requested.connect(self.on_ingest_clicked)
        layout.addWidget(self.state_widget)

        # §49 Offline Banner
        self._offline_banner = QLabel(
            "Offline Mode — Browsing existing Knowledge Bases is available. AI Chat requires an active provider connection."
        )
        self._offline_banner.setWordWrap(True)
        self._offline_banner.setStyleSheet(
            "font-size: 11px; padding: 8px 16px; border-radius: 6px; "
            "background: rgba(234, 179, 8, 0.12); color: #ca8a04; border: 1px solid rgba(234, 179, 8, 0.3);"
        )
        self._offline_banner.setVisible(False)
        layout.addWidget(self._offline_banner)
        self._check_online_status()

        # ── Main Splitter ────────────────────────────────────────────────────
        splitter = QSplitter(Qt.Horizontal)

        # Left Pane: Repository Intelligence & Metadata
        left_pane = QFrame()
        left_pane.setProperty("class", "g-pane")
        left_layout = QVBoxLayout(left_pane)
        left_layout.setContentsMargins(16, 16, 16, 16)
        left_layout.setSpacing(12)

        eyebrow = QLabel("REPOSITORY INTELLIGENCE")
        eyebrow.setProperty("class", "g-eyebrow")
        left_layout.addWidget(eyebrow)

        self.repo_title = QLabel("No Repository Ingested")
        self.repo_title.setStyleSheet("font-size: 16px; font-weight: 700;")
        left_layout.addWidget(self.repo_title)

        # Prominent Metadata Grid at the TOP of Left Pane
        self.meta_card = QFrame()
        self.meta_card.setStyleSheet(
            "QFrame { border: 1px solid palette(mid); border-radius: 8px; background: palette(alternate-base); }"
        )
        grid = QGridLayout(self.meta_card)
        grid.setContentsMargins(12, 12, 12, 12)
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(8)

        lbl_lic_title = QLabel("License:")
        lbl_lic_title.setStyleSheet("font-size: 11px; font-weight: 600; color: #71717a;")
        self.lbl_license = QLabel("—")
        self.lbl_license.setStyleSheet("font-size: 11px; font-weight: 600;")

        lbl_files_title = QLabel("Files:")
        lbl_files_title.setStyleSheet("font-size: 11px; font-weight: 600; color: #71717a;")
        self.lbl_files = QLabel("—")
        self.lbl_files.setStyleSheet("font-size: 11px;")

        lbl_stack_title = QLabel("Stack:")
        lbl_stack_title.setStyleSheet("font-size: 11px; font-weight: 600; color: #71717a;")
        self.lbl_stack = QLabel("—")
        self.lbl_stack.setStyleSheet("font-size: 11px;")
        self.lbl_stack.setWordWrap(True)

        lbl_arch_title = QLabel("Pattern:")
        lbl_arch_title.setStyleSheet("font-size: 11px; font-weight: 600; color: #71717a;")
        self.lbl_arch = QLabel("—")
        self.lbl_arch.setStyleSheet("font-size: 11px;")

        lbl_commit_title = QLabel("Commit:")
        lbl_commit_title.setStyleSheet("font-size: 11px; font-weight: 600; color: #71717a;")
        self.lbl_commit = QLabel("—")
        self.lbl_commit.setStyleSheet("font-size: 10px; font-family: monospace;")

        grid.addWidget(lbl_lic_title, 0, 0)
        grid.addWidget(self.lbl_license, 0, 1)
        grid.addWidget(lbl_files_title, 0, 2)
        grid.addWidget(self.lbl_files, 0, 3)
        grid.addWidget(lbl_stack_title, 1, 0)
        grid.addWidget(self.lbl_stack, 1, 1, 1, 3)
        grid.addWidget(lbl_arch_title, 2, 0)
        grid.addWidget(self.lbl_arch, 2, 1, 1, 3)
        grid.addWidget(lbl_commit_title, 3, 0)
        grid.addWidget(self.lbl_commit, 3, 1, 1, 3)

        left_layout.addWidget(self.meta_card)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setFixedHeight(4)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.hide()
        left_layout.addWidget(self.progress_bar)

        # Quantitative progress label (§48)
        self._progress_pct_lbl = QLabel("")
        self._progress_pct_lbl.setStyleSheet(
            "font-size: 11px; font-family: monospace; color: #71717a; padding: 2px 0;"
        )
        self._progress_pct_lbl.setVisible(False)
        left_layout.addWidget(self._progress_pct_lbl)

        # Secret Warning Banner (§53)
        self._secret_banner = QLabel("")
        self._secret_banner.setWordWrap(True)
        self._secret_banner.setStyleSheet(
            "font-size: 11px; padding: 8px 12px; border-radius: 6px; "
            "background: rgba(234, 179, 8, 0.12); color: #ca8a04; border: 1px solid rgba(234, 179, 8, 0.3);"
        )
        self._secret_banner.setVisible(False)
        left_layout.addWidget(self._secret_banner)

        # Log Header
        log_header = QHBoxLayout()
        log_lbl = QLabel("ANALYSIS LOGS")
        log_lbl.setProperty("class", "g-eyebrow")
        btn_clear_log = QPushButton("Clear Log")
        btn_clear_log.setProperty("class", "g-btn-ghost")
        btn_clear_log.setFixedHeight(26)
        btn_clear_log.setStyleSheet("font-size: 10px; padding: 2px 8px;")
        btn_clear_log.clicked.connect(lambda: self.log_output.clear())
        log_header.addWidget(log_lbl)
        log_header.addStretch()
        log_header.addWidget(btn_clear_log)
        left_layout.addLayout(log_header)

        self.log_output = QPlainTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setPlaceholderText("Live analysis execution logs will appear here…")
        self.log_output.setStyleSheet("font-family: 'Geist Mono', 'Consolas', monospace; font-size: 11px; line-height: 1.4;")
        left_layout.addWidget(self.log_output, 1)

        # Right Pane: Streamed Prompt Workspace
        right_pane = QFrame()
        right_pane.setProperty("class", "g-pane")
        right_layout = QVBoxLayout(right_pane)
        right_layout.setContentsMargins(16, 16, 16, 16)
        right_layout.setSpacing(10)

        right_header = QHBoxLayout()
        right_eyebrow = QLabel("STREAMED PROMPT WORKSPACE")
        right_eyebrow.setProperty("class", "g-eyebrow")
        right_header.addWidget(right_eyebrow)
        right_header.addStretch()

        self.btn_chat_ai = QPushButton("Chat with AI")
        self.btn_chat_ai.setProperty("class", "g-btn-ghost")
        self.btn_chat_ai.hide()
        self.btn_chat_ai.clicked.connect(self.on_chat_ai_clicked)
        right_header.addWidget(self.btn_chat_ai)

        self.btn_copy_prompt = QPushButton("Copy Prompt")
        self.btn_copy_prompt.setProperty("class", "g-btn-ghost")
        self.btn_copy_prompt.clicked.connect(self.on_copy_prompt_clicked)
        right_header.addWidget(self.btn_copy_prompt)

        right_layout.addLayout(right_header)

        self.prompt_editor = QPlainTextEdit()
        self.prompt_editor.setReadOnly(True)
        self.prompt_editor.setPlaceholderText(
            "Streamed AI recreation prompt tokens will appear here in real time…\n\n"
            "Enter a GitHub URL above and click Ingest Repository to begin."
        )
        self.prompt_editor.setStyleSheet("font-family: 'Geist Mono', 'Consolas', monospace; font-size: 12px; line-height: 1.5;")
        right_layout.addWidget(self.prompt_editor, 1)

        splitter.addWidget(left_pane)
        splitter.addWidget(right_pane)
        splitter.setSizes([340, 660])
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        layout.addWidget(splitter, 1)

    def bind_vm(self):
        self.vm.progress_updated.connect(self.on_progress)
        self.vm.metadata_received.connect(self.on_meta)
        self.vm.token_received.connect(self.on_token)
        self.vm.analysis_failed.connect(self.on_failed)
        self.vm.analysis_completed.connect(self.on_completed)
        self.vm.state_changed.connect(self.on_state_changed)
        if hasattr(self.vm, 'progress_pct_updated'):
            self.vm.progress_pct_updated.connect(self.on_progress_pct)
        if hasattr(self.vm, 'secrets_found'):
            self.vm.secrets_found.connect(self.on_secrets_found)

    def on_ingest_clicked(self):
        url = self.url_input.text().strip()
        if not url:
            self.state_widget.set_error("Repository URL is required.", override_msg="Please enter a valid GitHub repository URL.")
            return
        if not url.startswith("https://github.com/"):
            self.state_widget.set_error("Invalid GitHub URL format", override_msg="Repository URL must start with https://github.com/owner/repository")
            return
        self.log_output.clear()
        self.prompt_editor.clear()
        self._secret_banner.setVisible(False)
        self._progress_pct_lbl.setVisible(False)
        self.state_widget.set_loading("Connecting to GitHub and analyzing repository...")
        self.vm.start_analysis(url, prompt_type="Clone Prompt")

    def on_cancel_clicked(self):
        self.vm.cancel_analysis()
        self.log_output.appendPlainText("> Analysis cancelled by user.")
        self.state_widget.set_idle("Analysis cancelled by user.")

    def on_copy_prompt_clicked(self):
        text = self.prompt_editor.toPlainText()
        if text.strip():
            QApplication.clipboard().setText(text)
            self.btn_copy_prompt.setText("Copied!")
            QTimer.singleShot(2000, lambda: self.btn_copy_prompt.setText("Copy Prompt"))

    def on_progress(self, msg: str):
        self.log_output.appendPlainText(f"> {msg}")
        self.state_widget.set_loading(msg)
        if self._progress_pct_lbl.isVisible():
            current_text = self._progress_pct_lbl.text().split(" — ")[0]
            self._progress_pct_lbl.setText(f"{current_text} — {msg}")

    def on_meta(self, meta: dict):
        self.repo_title.setText(meta.get("repo_name", "Repository"))
        self.lbl_license.setText(meta.get('source_license', 'none'))
        self.lbl_files.setText(f"{meta.get('file_count', 0)} files")
        langs = ", ".join(meta.get("languages", [])) or "Unknown"
        self.lbl_stack.setText(langs)
        self.lbl_arch.setText(meta.get('arch_pattern', '—'))
        commit = meta.get("commit_sha", "")
        branch = meta.get("branch", "")
        tag = meta.get("repo_tag", "")
        ver_parts = []
        if commit:
            ver_parts.append(f"{commit[:8]} ({branch or 'main'})")  
        if tag:
            ver_parts.append(f"tag: {tag}")
        self.lbl_commit.setText("  ·  ".join(ver_parts) if ver_parts else "N/A")
        sc = meta.get("secret_count", 0)
        if sc > 0:
            self._secret_banner.setText(
                f"⚠  {sc} potential secret(s) detected — see log. Secrets are NEVER transmitted to AI."
            )
            self._secret_banner.setVisible(True)

    def on_progress_pct(self, done: int, total: int):
        if total > 0:
            pct = int((done / total) * 100)
            self.progress_bar.setRange(0, total)
            self.progress_bar.setValue(done)
            self._progress_pct_lbl.setVisible(True)
            self._progress_pct_lbl.setText(f"Analyzing: {done:,} / {total:,} files ({pct}%)")
            self.state_widget.set_loading(f"Analyzing repository code...", progress=done, total=total)

    def on_secrets_found(self, findings: list):
        high = [f for f in findings if f.get("severity") == "high"]
        if high:
            self._secret_banner.setText(
                f"⚠  {len(high)} high-severity secret pattern(s) detected. Review the log below."
            )
            self._secret_banner.setVisible(True)

    def _check_online_status(self):
        try:
            import socket
            socket.setdefaulttimeout(2)
            socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(("api.github.com", 443))
            self._offline_banner.setVisible(False)
        except Exception:
            self._offline_banner.setVisible(True)

    def on_token(self, token: str):
        self.prompt_editor.insertPlainText(token)
        sb = self.prompt_editor.verticalScrollBar()
        sb.setValue(sb.maximum())

    def on_failed(self, err: str):
        self.log_output.appendPlainText(f"\n[ERROR] {err}")
        self.state_widget.set_error(err)

    def on_chat_ai_clicked(self):
        if self._current_session_id:
            self.chat_requested.emit(self._current_session_id)

    def on_completed(self, session_id: int, prompt: str):
        self._current_session_id = session_id
        self.btn_chat_ai.show()
        self.log_output.appendPlainText(f"\n[DONE] Session #{session_id} persisted to SQLite.")
        self.state_widget.set_success(f"Analysis complete! Session #{session_id} saved to Knowledge Base.")

    def on_state_changed(self, is_analyzing: bool):
        self.ingest_btn.setEnabled(not is_analyzing)
        self.cancel_btn.setVisible(is_analyzing)
        self.progress_bar.setVisible(is_analyzing)
        self.ingest_btn.setText("Analyzing…" if is_analyzing else "Ingest Repository")
        if not is_analyzing:
            self.progress_bar.setRange(0, 0)
            self._progress_pct_lbl.setVisible(False)
            self._progress_pct_lbl.setVisible(False)
