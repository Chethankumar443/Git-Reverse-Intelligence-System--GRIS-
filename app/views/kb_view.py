import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QPushButton, QPlainTextEdit, QFrame, QSplitter, QFileDialog, QMessageBox,
    QLineEdit, QApplication, QTabWidget
)
from PySide6.QtCore import Qt
from app.viewmodels.session_vm import SessionViewModel


class KnowledgeBaseView(QWidget):
    """Desktop Workspace View for browsing past SQLite session history, searching FTS5 indexes,

    viewing License Compliance Reports (§62), and exporting PDF/Markdown prompts.
    """

    def __init__(self, session_vm: SessionViewModel, parent=None):
        super().__init__(parent)
        self.vm = session_vm
        self.init_ui()
        self.bind_vm()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Top Action Bar
        top_bar = QFrame()
        top_bar.setProperty("class", "g-pane")
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(12, 10, 12, 10)
        top_layout.setSpacing(8)

        title = QLabel("Knowledge Base & Session History")
        title.setStyleSheet("font-size: 14px; font-weight: 600;")

        self.btn_refresh = QPushButton("Refresh")
        self.btn_refresh.setProperty("class", "g-btn-ghost")
        self.btn_refresh.clicked.connect(self.on_refresh_clicked)

        self.btn_chat_repo = QPushButton("Chat About Repo")
        self.btn_chat_repo.setProperty("class", "g-btn-ghost")
        self.btn_chat_repo.clicked.connect(self.on_chat_repo_clicked)

        self.btn_license = QPushButton("License Compliance")
        self.btn_license.setProperty("class", "g-btn-ghost")
        self.btn_license.clicked.connect(self.on_license_report_clicked)

        self.btn_copy = QPushButton("Copy Prompt")
        self.btn_copy.setProperty("class", "g-btn-ghost")
        self.btn_copy.clicked.connect(self.on_copy_clicked)

        self.btn_export_md = QPushButton("Export Markdown")
        self.btn_export_md.setProperty("class", "g-btn-ghost")
        self.btn_export_md.clicked.connect(self.on_export_md_clicked)

        self.btn_export_pdf = QPushButton("Export PDF")
        self.btn_export_pdf.setProperty("class", "g-btn-solid")
        self.btn_export_pdf.clicked.connect(self.on_export_pdf_clicked)

        top_layout.addWidget(title)
        top_layout.addStretch()
        top_layout.addWidget(self.btn_refresh)
        top_layout.addWidget(self.btn_chat_repo)
        top_layout.addWidget(self.btn_license)
        top_layout.addWidget(self.btn_copy)
        top_layout.addWidget(self.btn_export_md)
        top_layout.addWidget(self.btn_export_pdf)

        layout.addWidget(top_bar)

        # Reusable Async State Contract Widget for Export & Refresh operations
        from app.views.components import AsyncStateWidget
        self.state_widget = AsyncStateWidget()
        layout.addWidget(self.state_widget)

        # Main Splitter
        splitter = QSplitter(Qt.Horizontal)

        # Left History List Pane
        left_pane = QFrame()
        left_pane.setProperty("class", "g-pane")
        left_layout = QVBoxLayout(left_pane)
        left_layout.setContentsMargins(12, 12, 12, 12)
        left_layout.setSpacing(8)

        eyebrow = QLabel("PERSISTED SESSIONS (SQLITE FTS5)")
        eyebrow.setProperty("class", "g-eyebrow")
        left_layout.addWidget(eyebrow)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Filter sessions by name or license...")
        self.search_input.textChanged.connect(self.on_search_changed)
        left_layout.addWidget(self.search_input)

        self.session_list = QListWidget()
        self.session_list.itemSelectionChanged.connect(self.on_session_selected)
        left_layout.addWidget(self.session_list, 1)

        # Delete & Clear Actions
        act_row = QHBoxLayout()
        self.btn_delete = QPushButton("Delete Selected")
        self.btn_delete.setProperty("class", "g-btn-ghost")
        self.btn_delete.clicked.connect(self.on_delete_clicked)

        self.btn_clear_all = QPushButton("Clear History")
        self.btn_clear_all.setProperty("class", "g-btn-ghost")
        self.btn_clear_all.clicked.connect(self.on_clear_all_clicked)

        act_row.addWidget(self.btn_delete)
        act_row.addWidget(self.btn_clear_all)
        left_layout.addLayout(act_row)

        # Right View Tabs (Prompt Preview vs License Report)
        right_pane = QFrame()
        right_pane.setProperty("class", "g-pane")
        right_layout = QVBoxLayout(right_pane)
        right_layout.setContentsMargins(14, 14, 14, 14)
        right_layout.setSpacing(8)

        self.lbl_session_title = QLabel("Select a Session from Left List")
        self.lbl_session_title.setStyleSheet("font-size: 14px; font-weight: 600; color: #171717;")
        right_layout.addWidget(self.lbl_session_title)

        self.lbl_session_meta = QLabel("License: — | Created: — | Model: —")
        self.lbl_session_meta.setStyleSheet("font-size: 11px; color: #71717a;")
        right_layout.addWidget(self.lbl_session_meta)

        self.tabs = QTabWidget()

        # Tab 1: Prompt Content
        self.prompt_preview = QPlainTextEdit()
        self.prompt_preview.setReadOnly(True)
        self.prompt_preview.setPlaceholderText("Persisted prompt content will load here...")
        self.prompt_preview.setStyleSheet("font-family: 'Geist Mono', monospace; font-size: 12px; line-height: 1.5;")
        self.tabs.addTab(self.prompt_preview, "Recreation Prompt")

        # Tab 2: License Compliance Report (§62)
        self.license_report_edit = QPlainTextEdit()
        self.license_report_edit.setReadOnly(True)
        self.license_report_edit.setPlaceholderText("License compliance breakdown will load here...")
        self.license_report_edit.setStyleSheet("font-family: 'Geist Mono', monospace; font-size: 12px; line-height: 1.5;")
        self.tabs.addTab(self.license_report_edit, "License Report")

        right_layout.addWidget(self.tabs, 1)

        splitter.addWidget(left_pane)
        splitter.addWidget(right_pane)
        splitter.setSizes([320, 580])

        layout.addWidget(splitter, 1)

    def select_session_by_id(self, session_id: int):
        """Programmatically select a session in the list by its ID."""
        for i in range(self.session_list.count()):
            item = self.session_list.item(i)
            if item and item.data(Qt.UserRole) == session_id:
                self.session_list.setCurrentRow(i)
                return

    def bind_vm(self):
        self.vm.sessions_loaded.connect(self.on_sessions_loaded)
        self.vm.session_selected.connect(self.on_session_data_loaded)
        self.vm.export_finished.connect(self.on_export_finished)
        self.vm.refresh_sessions()

    def on_refresh_clicked(self):
        self.search_input.clear()
        self.vm.refresh_sessions()

    def on_chat_repo_clicked(self):
        self.vm.request_chat_for_active_session()

    def on_license_report_clicked(self):
        self.tabs.setCurrentIndex(1)
        rep = self.vm.generate_license_report()
        if rep and "report_text" in rep:
            self.license_report_edit.setPlainText(rep["report_text"])
        else:
            self.license_report_edit.setPlainText("Select an active repository session first.")

    def on_search_changed(self, text: str):
        self.vm.search_sessions(text)

    def on_copy_clicked(self):
        # Copy active tab's text
        cur_widget = self.tabs.currentWidget()
        text = cur_widget.toPlainText() if hasattr(cur_widget, "toPlainText") else ""
        if text:
            QApplication.clipboard().setText(text)
            self.btn_copy.setText("Copied!")
            from PySide6.QtCore import QTimer
            QTimer.singleShot(2000, lambda: self.btn_copy.setText("Copy Prompt"))

    def on_delete_clicked(self):
        items = self.session_list.selectedItems()
        if not items:
            return
        session_id = items[0].data(Qt.UserRole)
        res = QMessageBox.question(self, "Confirm Delete", "Are you sure you want to delete this session from SQLite database?")
        if res == QMessageBox.Yes:
            self.vm.delete_session(session_id)

    def on_clear_all_clicked(self):
        res = QMessageBox.warning(self, "Clear History", "Are you sure you want to clear all persistent session records?", QMessageBox.Yes | QMessageBox.No)
        if res == QMessageBox.Yes:
            self.vm.clear_all_history()

    def on_sessions_loaded(self, sessions: list):
        self.session_list.clear()
        for s in sessions:
            item = QListWidgetItem(f"{s['repo_name']} ({s['language']})")
            item.setData(Qt.UserRole, s['id'])
            self.session_list.addItem(item)

        if sessions:
            self.session_list.setCurrentRow(0)
        else:
            self.lbl_session_title.setText("No Repository Sessions Found")
            self.lbl_session_meta.setText("Analyze a GitHub repository to build your Knowledge Base.")
            self.prompt_preview.setPlainText(
                "No persistent sessions found in SQLite Knowledge Base.\n\n"
                "To create your first Knowledge Base entry:\n"
                "1. Go to the Ingestion view\n"
                "2. Paste a GitHub repository URL\n"
                "3. Click 'Ingest Repository'"
            )
            self.license_report_edit.setPlainText("No session data available for License Compliance report.")

    def on_session_selected(self):
        items = self.session_list.selectedItems()
        if items:
            session_id = items[0].data(Qt.UserRole)
            self.vm.select_session(session_id)

    def on_session_data_loaded(self, s: dict):
        commit = s.get("commit_sha", "")
        branch = s.get("branch", "")
        ver_str = f"v{s.get('version_number', 1)}"
        commit_str = f" | Commit: {commit[:8]} ({branch})" if commit else ""

        self.lbl_session_title.setText(f"{s.get('repo_name', 'Session Record')}  [{ver_str}]")
        self.lbl_session_meta.setText(
            f"License: {s.get('source_license', 'none')} | "
            f"Created: {s.get('created_at', '')} | "
            f"Model: {s.get('model_used', 'gpt-4o')}"
            f"{commit_str}"
        )
        self.prompt_preview.setPlainText(s.get("generated_prompt", ""))

        # Populate License Report tab automatically
        rep = self.vm.generate_license_report()
        if rep and "report_text" in rep:
            self.license_report_edit.setPlainText(rep["report_text"])

    def on_export_md_clicked(self):
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Export Markdown Prompt", os.path.expanduser("~/Documents/prompt.md"), "Markdown Files (*.md)"
        )
        if filepath:
            self.state_widget.set_loading(f"Exporting prompt to Markdown file...")
            self.vm.export_session_markdown(filepath)

    def on_export_pdf_clicked(self):
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Export PDF Prompt", os.path.expanduser("~/Documents/prompt.pdf"), "PDF Files (*.pdf);;HTML Files (*.html)"
        )
        if filepath:
            self.state_widget.set_loading(f"Exporting prompt to PDF document...")
            self.vm.export_session_pdf(filepath)

    def on_export_finished(self, success: bool, msg: str):
        if success:
            self.state_widget.set_success(msg)
        else:
            self.state_widget.set_error(msg)
