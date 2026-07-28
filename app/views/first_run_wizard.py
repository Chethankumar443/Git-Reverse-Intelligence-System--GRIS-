"""
First Launch Wizard — Enterprise 5-step onboarding dialog (PRD §66).

Shown on first run (first_run_complete = False in config).
Steps: 1 Welcome → 2 Configure Provider → 3 Test Connection → 4 Storage → 5 Ready.
"""
import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QStackedWidget, QWidget, QFrame, QComboBox, QProgressBar, QFileDialog,
    QApplication, QGridLayout
)
from PySide6.QtCore import Qt, Signal, QThread
from PySide6.QtGui import QFont
from app.services.secrets import SecretsManager
from app.services.llm_client import detect_provider_from_key


class _TestWorker(QThread):
    result = Signal(bool, str)

    def __init__(self, api_key, base_url, model_id, parent=None):
        super().__init__(parent)
        self._key = api_key
        self._url = base_url
        self._model = model_id

    def run(self):
        try:
            from app.services.llm_client import LLMClient
            client = LLMClient(api_key=self._key, base_url=self._url, model_id=self._model)
            ok, msg = client.test_connection()
            self.result.emit(ok, msg)
        except Exception as e:
            self.result.emit(False, str(e))


class FirstRunWizard(QDialog):
    """5-step onboarding wizard. Emits completed() when finished."""

    completed = Signal()

    STEPS = ["1. Welcome", "2. Provider", "3. Test", "4. Storage", "5. Ready"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Git Reverse — Setup Wizard")
        self.setMinimumSize(660, 520)
        self.setModal(True)
        self._current_step = 0
        self._test_worker = None

        # Inherit parent application stylesheet
        app = QApplication.instance()
        if app:
            self.setStyleSheet(app.styleSheet())

        self._init_ui()

    def _init_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Step Indicator Header
        self._header = QFrame()
        self._header.setFixedHeight(56)
        self._header.setStyleSheet(
            "QFrame { border-bottom: 1px solid palette(mid); }"
        )
        h_row = QHBoxLayout(self._header)
        h_row.setContentsMargins(24, 0, 24, 0)
        h_row.setSpacing(8)

        self._step_widgets = []
        for i, step in enumerate(self.STEPS):
            step_lbl = QLabel(step)
            step_lbl.setStyleSheet("font-size: 12px; font-weight: 500; padding: 4px 10px; border-radius: 12px;")
            self._step_widgets.append(step_lbl)
            h_row.addWidget(step_lbl)

            if i < len(self.STEPS) - 1:
                sep = QLabel("›")
                sep.setStyleSheet("color: #71717a; font-size: 14px;")
                h_row.addWidget(sep)

        h_row.addStretch()
        outer.addWidget(self._header)

        # Page Stack
        self._stack = QStackedWidget()
        self._stack.addWidget(self._build_welcome())
        self._stack.addWidget(self._build_provider())
        self._stack.addWidget(self._build_test())
        self._stack.addWidget(self._build_storage())
        self._stack.addWidget(self._build_complete())
        outer.addWidget(self._stack, 1)

        # Footer Navigation
        footer = QFrame()
        footer.setFixedHeight(64)
        footer.setStyleSheet("QFrame { border-top: 1px solid palette(mid); }")
        f_row = QHBoxLayout(footer)
        f_row.setContentsMargins(24, 0, 24, 0)

        self._btn_back = QPushButton("Back")
        self._btn_back.setProperty("class", "g-btn-ghost")
        self._btn_back.setFixedHeight(36)
        self._btn_back.setEnabled(False)
        self._btn_back.clicked.connect(self._go_back)

        self._btn_next = QPushButton("Continue →")
        self._btn_next.setProperty("class", "g-btn-solid")
        self._btn_next.setFixedHeight(36)
        self._btn_next.setMinimumWidth(120)
        self._btn_next.clicked.connect(self._go_next)

        f_row.addWidget(self._btn_back)
        f_row.addStretch()
        f_row.addWidget(self._btn_next)
        outer.addWidget(footer)

        self._update_step_styles()

    # ── Step 1: Welcome ──────────────────────────────────────────────────────

    def _build_welcome(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(36, 32, 36, 24)
        layout.setSpacing(16)

        title = QLabel("Welcome to Git Reverse")
        title.setFont(QFont("Segoe UI", 22, QFont.Bold))
        layout.addWidget(title)

        subtitle = QLabel(
            "Git Reverse reverse-engineers any GitHub repository into a durable, "
            "evidence-backed Knowledge Base — enabling instant architectural analysis and "
            "context-grounded AI chat without repeatedly uploading raw source files."
        )
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("font-size: 13px; color: #71717a; line-height: 1.5;")
        layout.addWidget(subtitle)

        layout.addSpacing(8)

        # Enterprise Feature Cards Grid
        grid = QGridLayout()
        grid.setSpacing(12)

        cards_data = [
            ("Local Analysis Guarantee", "Source code remains entirely on your machine. Only compressed Knowledge Base summaries are transmitted."),
            ("Persistent Knowledge Engine", "Codebases are indexed once into SQLite FTS5 for instant sub-second retrieval across sessions."),
            ("Evidence-Grounded AI", "AI responses strictly cite exact file paths, line ranges, and AST symbols from your repository."),
            ("Bring Your Own Key", "Supports OpenRouter, OpenAI, Groq, DeepSeek, and local offline Ollama endpoints."),
        ]

        for idx, (head, body) in enumerate(cards_data):
            card = QFrame()
            card.setProperty("class", "g-pane")
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(14, 12, 14, 12)
            card_layout.setSpacing(4)

            h_lbl = QLabel(head)
            h_lbl.setStyleSheet("font-size: 13px; font-weight: 600;")
            b_lbl = QLabel(body)
            b_lbl.setWordWrap(True)
            b_lbl.setStyleSheet("font-size: 11px; color: #71717a;")

            card_layout.addWidget(h_lbl)
            card_layout.addWidget(b_lbl)

            r = idx // 2
            c = idx % 2
            grid.addWidget(card, r, c)

        layout.addLayout(grid)
        layout.addStretch()
        return w

    # ── Step 2: Provider Configuration ──────────────────────────────────────

    def _build_provider(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(36, 32, 36, 24)
        layout.setSpacing(14)

        title = QLabel("Configure LLM Provider")
        title.setFont(QFont("Segoe UI", 18, QFont.Bold))
        layout.addWidget(title)

        sub = QLabel(
            "Paste your API key below. Git Reverse automatically detects your provider "
            "and saves your credentials securely in your operating system's Credential Store."
        )
        sub.setWordWrap(True)
        sub.setStyleSheet("font-size: 12px; color: #71717a;")
        layout.addWidget(sub)

        layout.addSpacing(10)

        # Provider Card
        card = QFrame()
        card.setProperty("class", "g-pane")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(18, 16, 18, 16)
        card_layout.setSpacing(12)

        key_lbl = QLabel("API Key:")
        key_lbl.setStyleSheet("font-weight: 600; font-size: 12px;")
        card_layout.addWidget(key_lbl)

        self._wiz_key_input = QLineEdit()
        self._wiz_key_input.setEchoMode(QLineEdit.Password)
        self._wiz_key_input.setPlaceholderText("Paste API key (sk-or-v1-… / gsk_… / sk-proj-…)")
        self._wiz_key_input.setMinimumHeight(38)
        self._wiz_key_input.textChanged.connect(self._on_key_changed)
        card_layout.addWidget(self._wiz_key_input)

        prov_row = QHBoxLayout()
        prov_lbl = QLabel("Provider:")
        prov_lbl.setStyleSheet("font-weight: 600; font-size: 12px;")
        prov_lbl.setFixedWidth(80)
        self._wiz_preset = QComboBox()
        self._wiz_preset.addItems(["OpenRouter", "Groq", "OpenAI", "DeepSeek", "Ollama Local", "Custom"])
        self._wiz_preset.setMinimumHeight(34)
        prov_row.addWidget(prov_lbl)
        prov_row.addWidget(self._wiz_preset, 1)
        card_layout.addLayout(prov_row)

        url_row = QHBoxLayout()
        url_lbl = QLabel("Base URL:")
        url_lbl.setStyleSheet("font-weight: 600; font-size: 12px;")
        url_lbl.setFixedWidth(80)
        self._wiz_url = QLineEdit()
        self._wiz_url.setText("https://openrouter.ai/api/v1")
        self._wiz_url.setMinimumHeight(34)
        url_row.addWidget(url_lbl)
        url_row.addWidget(self._wiz_url, 1)
        card_layout.addLayout(url_row)

        layout.addWidget(card)

        self._wiz_key_status = QLabel("Paste an API key above to proceed.")
        self._wiz_key_status.setWordWrap(True)
        self._wiz_key_status.setStyleSheet(
            "font-size: 11px; padding: 8px 12px; border-radius: 6px; "
            "background: rgba(113, 113, 122, 0.1); color: #71717a;"
        )
        layout.addWidget(self._wiz_key_status)
        layout.addStretch()
        return w

    # ── Step 3: Test Connection ─────────────────────────────────────────────

    def _build_test(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(36, 32, 36, 24)
        layout.setSpacing(14)

        title = QLabel("Verify Connectivity")
        title.setFont(QFont("Segoe UI", 18, QFont.Bold))
        layout.addWidget(title)

        sub = QLabel(
            "Test communication with your LLM provider endpoint to ensure "
            "your API key and base URL are configured correctly."
        )
        sub.setWordWrap(True)
        sub.setStyleSheet("font-size: 12px; color: #71717a;")
        layout.addWidget(sub)

        layout.addSpacing(12)

        card = QFrame()
        card.setProperty("class", "g-pane")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        card_layout.setSpacing(14)

        self._btn_test = QPushButton("Test API Connection")
        self._btn_test.setProperty("class", "g-btn-solid")
        self._btn_test.setMinimumHeight(40)
        self._btn_test.clicked.connect(self._run_connection_test)
        card_layout.addWidget(self._btn_test)

        self._test_progress = QProgressBar()
        self._test_progress.setRange(0, 0)
        self._test_progress.setVisible(False)
        self._test_progress.setFixedHeight(4)
        card_layout.addWidget(self._test_progress)

        self._test_result = QLabel("Click Test API Connection to verify.")
        self._test_result.setWordWrap(True)
        self._test_result.setStyleSheet(
            "font-size: 12px; padding: 12px 14px; border-radius: 6px; "
            "background: rgba(113, 113, 122, 0.08); color: #71717a;"
        )
        card_layout.addWidget(self._test_result)
        layout.addWidget(card)

        note = QLabel("You can also skip this step and adjust your key anytime in Settings.")
        note.setStyleSheet("font-size: 11px; color: #a1a1aa;")
        note.setAlignment(Qt.AlignCenter)
        layout.addWidget(note)
        layout.addStretch()
        return w

    # ── Step 4: Storage Setup ────────────────────────────────────────────────

    def _build_storage(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(36, 32, 36, 24)
        layout.setSpacing(14)

        title = QLabel("Storage & Privacy Isolation")
        title.setFont(QFont("Segoe UI", 18, QFont.Bold))
        layout.addWidget(title)

        sub = QLabel(
            "Git Reverse stores Knowledge Bases, session records, and settings in an isolated "
            "local directory. Your data is kept separate from application binaries."
        )
        sub.setWordWrap(True)
        sub.setStyleSheet("font-size: 12px; color: #71717a;")
        layout.addWidget(sub)

        layout.addSpacing(12)

        card = QFrame()
        card.setProperty("class", "g-pane")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(18, 16, 18, 16)
        card_layout.setSpacing(12)

        appdata = os.getenv("APPDATA") or os.path.expanduser("~")
        default_dir = os.path.join(appdata, "GitReverse")

        dir_row = QHBoxLayout()
        dir_lbl = QLabel("Data Directory:")
        dir_lbl.setStyleSheet("font-weight: 600;")
        dir_lbl.setFixedWidth(120)
        self._wiz_dir_input = QLineEdit(default_dir)
        self._wiz_dir_input.setMinimumHeight(36)
        btn_browse = QPushButton("Browse…")
        btn_browse.setProperty("class", "g-btn-ghost")
        btn_browse.setFixedHeight(36)
        btn_browse.clicked.connect(self._browse_dir)
        dir_row.addWidget(dir_lbl)
        dir_row.addWidget(self._wiz_dir_input, 1)
        dir_row.addWidget(btn_browse)
        card_layout.addLayout(dir_row)

        layout.addWidget(card)

        note = QLabel(
            "✓ Application upgrades will preserve all your Knowledge Bases and settings."
        )
        note.setWordWrap(True)
        note.setStyleSheet(
            "font-size: 11px; padding: 10px 14px; border-radius: 6px; "
            "background: rgba(22, 101, 52, 0.1); color: #166534; border: 1px solid rgba(134, 239, 172, 0.4);"
        )
        layout.addWidget(note)
        layout.addStretch()
        return w

    # ── Step 5: Complete ─────────────────────────────────────────────────────

    def _build_complete(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(36, 32, 36, 24)
        layout.setSpacing(16)

        title = QLabel("Setup Complete")
        title.setFont(QFont("Segoe UI", 22, QFont.Bold))
        layout.addWidget(title)

        sub = QLabel(
            "Git Reverse is ready for use. Enter a GitHub repository URL in the "
            "Analyze tab to reverse-engineer your first codebase."
        )
        sub.setWordWrap(True)
        sub.setStyleSheet("font-size: 13px; color: #71717a;")
        layout.addWidget(sub)

        layout.addSpacing(8)

        self._complete_summary = QLabel("")
        self._complete_summary.setWordWrap(True)
        self._complete_summary.setStyleSheet(
            "font-size: 12px; font-family: monospace; padding: 16px; border-radius: 8px; "
            "background: rgba(113, 113, 122, 0.08); border: 1px solid palette(mid);"
        )
        layout.addWidget(self._complete_summary)
        layout.addStretch()
        return w

    # ── Navigation & Helper Methods ──────────────────────────────────────────

    def _update_step_styles(self):
        idx = self._current_step
        self._btn_back.setEnabled(idx > 0)
        is_last = idx == len(self.STEPS) - 1
        self._btn_next.setText("Finish & Launch" if is_last else "Continue →")

        for i, lbl in enumerate(self._step_widgets):
            if i == idx:
                lbl.setStyleSheet(
                    "font-size: 11px; font-weight: 700; padding: 4px 10px; border-radius: 12px; "
                    "background: palette(highlight); color: palette(highlighted-text);"
                )
            elif i < idx:
                lbl.setStyleSheet(
                    "font-size: 11px; font-weight: 600; padding: 4px 10px; border-radius: 12px; "
                    "background: rgba(113, 113, 122, 0.15); color: #71717a;"
                )
            else:
                lbl.setStyleSheet(
                    "font-size: 11px; font-weight: 500; padding: 4px 10px; border-radius: 12px; "
                    "color: #71717a;"
                )

    def _go_next(self):
        step = self._current_step
        if step == len(self.STEPS) - 1:
            self._finish()
            return
        if step == 1:
            key = self._wiz_key_input.text().strip()
            if key:
                SecretsManager.set_api_key(key)
                base_url = self._wiz_url.text().strip()
                preset = self._wiz_preset.currentText()
                SecretsManager.save_config({"provider_preset": preset, "base_url": base_url})

        self._current_step += 1
        self._stack.setCurrentIndex(self._current_step)
        self._update_step_styles()
        if self._current_step == len(self.STEPS) - 1:
            self._populate_complete()

    def _go_back(self):
        if self._current_step > 0:
            self._current_step -= 1
            self._stack.setCurrentIndex(self._current_step)
            self._update_step_styles()

    def _finish(self):
        config = SecretsManager.load_config()
        config["first_run_complete"] = True
        SecretsManager.save_config(config)
        self.completed.emit()
        self.accept()

    def _on_key_changed(self, text: str):
        if len(text.strip()) >= 10:
            provider, url = detect_provider_from_key(text)
            self._wiz_preset.setCurrentText(provider)
            self._wiz_url.setText(url)
            self._wiz_key_status.setText(f"✓ Detected Provider: {provider} ({url})")
            self._wiz_key_status.setStyleSheet(
                "font-size: 11px; padding: 8px 12px; border-radius: 6px; "
                "background: rgba(22, 101, 52, 0.1); color: #166534; border: 1px solid rgba(134, 239, 172, 0.4);"
            )
        else:
            self._wiz_key_status.setText("Paste an API key above to proceed.")
            self._wiz_key_status.setStyleSheet(
                "font-size: 11px; padding: 8px 12px; border-radius: 6px; "
                "background: rgba(113, 113, 122, 0.1); color: #71717a;"
            )

    def _run_connection_test(self):
        key = self._wiz_key_input.text().strip() if hasattr(self, "_wiz_key_input") else ""
        if not key:
            key = SecretsManager.get_api_key() or ""
        url = self._wiz_url.text().strip() if hasattr(self, "_wiz_url") else "https://api.openai.com/v1"
        model = "gpt-4o"

        self._btn_test.setEnabled(False)
        self._test_progress.setVisible(True)
        self._test_result.setText("Testing endpoint connection…")

        self._test_worker = _TestWorker(key, url, model, parent=self)
        self._test_worker.result.connect(self._on_test_result)
        self._test_worker.start()

    def _on_test_result(self, ok: bool, msg: str):
        self._test_progress.setVisible(False)
        self._btn_test.setEnabled(True)
        if ok:
            self._test_result.setText(f"✓ Connection Successful: {msg}")
            self._test_result.setStyleSheet(
                "font-size: 12px; padding: 12px 14px; border-radius: 6px; "
                "background: rgba(22, 101, 52, 0.1); color: #166534; border: 1px solid rgba(134, 239, 172, 0.4);"
            )
        else:
            self._test_result.setText(f"✗ Connection Failed: {msg}")
            self._test_result.setStyleSheet(
                "font-size: 12px; padding: 12px 14px; border-radius: 6px; "
                "background: rgba(153, 27, 27, 0.1); color: #991b1b; border: 1px solid rgba(252, 165, 165, 0.4);"
            )

    def _browse_dir(self):
        d = QFileDialog.getExistingDirectory(self, "Select Data Directory")
        if d:
            self._wiz_dir_input.setText(d)

    def _populate_complete(self):
        try:
            provider = f"{self._wiz_preset.currentText()} ({self._wiz_url.text()})"
        except Exception:
            provider = "Configured"
        try:
            data_dir = self._wiz_dir_input.text()
        except Exception:
            data_dir = os.path.join(os.getenv("APPDATA", "~"), "GitReverse")

        self._complete_summary.setText(
            f"Provider Configuration:\n  {provider}\n\n"
            f"Storage Location:\n  {data_dir}\n\n"
            f"Telemetry & Analytics:\n  Disabled by default (Opt-in available in Settings)"
        )
