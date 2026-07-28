"""
Repository Library View — Multi-repository management home base (PRD §56).

Shows all analyzed repositories as cards with Open, Re-analyze, Export, Delete actions.
Also displays KB version history per repository (PRD §51).
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QLineEdit, QMessageBox, QSizePolicy,
    QFileDialog, QMenu
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QAction
from app.services.database import DatabaseManager


class RepoCard(QFrame):
    """A single repository card in the library grid."""

    open_requested = Signal(int)
    reanalyze_requested = Signal(str)
    delete_requested = Signal(int, str)
    export_requested = Signal(int)

    def __init__(self, session_data: dict, parent=None):
        super().__init__(parent)
        self._data = session_data
        self.setProperty("class", "g-pane")
        self.setMinimumHeight(130)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(8)

        # Header row: repo name + version badge
        h_row = QHBoxLayout()
        name = self._data.get("repo_name", "Unknown")
        name_lbl = QLabel(name)
        name_lbl.setFont(QFont("Segoe UI", 14, QFont.Bold))
        h_row.addWidget(name_lbl, 1)

        ver = self._data.get("version_number", 1)
        ver_badge = QLabel(f"v{ver}")
        ver_badge.setStyleSheet(
            "font-size: 10px; font-weight: 700; padding: 2px 8px; border-radius: 10px; "
            "background: rgba(37, 99, 235, 0.1); color: #2563eb; border: 1px solid rgba(37, 99, 235, 0.3);"
        )
        h_row.addWidget(ver_badge)
        layout.addLayout(h_row)

        # Meta info row (No cheap emojis — clean, structured badges)
        lang = self._data.get("language", "Unknown")
        lic = self._data.get("source_license", "none")
        files = self._data.get("file_count", 0)
        commit = self._data.get("commit_sha", "")
        branch = self._data.get("branch", "")
        secrets = self._data.get("secret_warnings", 0)
        date = self._data.get("created_at", "")

        meta_parts = [f"Stack: {lang}", f"{files} files", f"License: {lic}"]
        if commit:
            meta_parts.append(f"Commit: {commit[:8]} ({branch or 'main'})")
        if date:
            meta_parts.append(f"Analyzed: {date[:10]}")

        meta_lbl = QLabel("  ·  ".join(meta_parts))
        meta_lbl.setStyleSheet("font-size: 11px; color: #71717a;")
        layout.addWidget(meta_lbl)

        # Secret warning (if any)
        if secrets > 0:
            warn = QLabel(f"⚠ {secrets} potential secret(s) detected — review recommended")
            warn.setStyleSheet(
                "font-size: 10px; padding: 3px 8px; border-radius: 4px; "
                "background: rgba(234, 179, 8, 0.12); color: #ca8a04; border: 1px solid rgba(234, 179, 8, 0.3);"
            )
            layout.addWidget(warn)

        # Actions row
        actions_row = QHBoxLayout()
        actions_row.setSpacing(8)

        btn_open = QPushButton("Open KB")
        btn_open.setProperty("class", "g-btn-solid")
        btn_open.setFixedHeight(32)
        btn_open.clicked.connect(lambda: self.open_requested.emit(self._data["id"]))
        actions_row.addWidget(btn_open)

        btn_reanalyze = QPushButton("Re-analyze")
        btn_reanalyze.setProperty("class", "g-btn-ghost")
        btn_reanalyze.setFixedHeight(32)
        btn_reanalyze.clicked.connect(lambda: self.reanalyze_requested.emit(self._data.get("repo_url", "")))
        actions_row.addWidget(btn_reanalyze)

        btn_export = QPushButton("Export")
        btn_export.setProperty("class", "g-btn-ghost")
        btn_export.setFixedHeight(32)
        btn_export.clicked.connect(lambda: self.export_requested.emit(self._data["id"]))
        actions_row.addWidget(btn_export)

        btn_delete = QPushButton("Delete")
        btn_delete.setProperty("class", "g-btn-ghost")
        btn_delete.setFixedHeight(32)
        btn_delete.setStyleSheet(
            "QPushButton { color: #dc2626; border-color: rgba(220, 38, 38, 0.3); }"
            "QPushButton:hover { background-color: rgba(220, 38, 38, 0.08); border-color: #dc2626; }"
        )
        btn_delete.clicked.connect(
            lambda: self.delete_requested.emit(self._data["id"], self._data.get("repo_name", ""))
        )
        actions_row.addWidget(btn_delete)
        actions_row.addStretch()

        layout.addLayout(actions_row)


class RepoLibraryView(QWidget):
    """Repository Library — lists all analyzed repositories with management actions (§56)."""

    open_kb_requested = Signal(int)       # session_id
    reanalyze_requested = Signal(str)     # repo_url

    def __init__(self, parent=None):
        super().__init__(parent)
        self._db = DatabaseManager()
        self._all_sessions = []
        self._init_ui()
        self.refresh()

    def _init_ui(self):
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        # Top bar
        top_bar = QFrame()
        top_bar.setFixedHeight(64)
        top_bar.setStyleSheet("QFrame { border-bottom: 1px solid palette(mid); }")
        top_row = QHBoxLayout(top_bar)
        top_row.setContentsMargins(24, 0, 24, 0)
        top_row.setSpacing(12)

        title = QLabel("Repository Library")
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        top_row.addWidget(title)
        top_row.addStretch()

        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("Search repositories by name, language, license…")
        self._search_input.setMinimumWidth(280)
        self._search_input.setMinimumHeight(36)
        self._search_input.textChanged.connect(self._filter_cards)
        top_row.addWidget(self._search_input)

        btn_refresh = QPushButton("Refresh")
        btn_refresh.setProperty("class", "g-btn-ghost")
        btn_refresh.setFixedHeight(36)
        btn_refresh.setToolTip("Refresh repository list")
        btn_refresh.clicked.connect(self.refresh)
        top_row.addWidget(btn_refresh)

        btn_import = QPushButton("Import Backup…")
        btn_import.setProperty("class", "g-btn-ghost")
        btn_import.setFixedHeight(36)
        btn_import.clicked.connect(self._import_backup)
        top_row.addWidget(btn_import)

        outer_layout.addWidget(top_bar)

        # Stats bar
        self._stats_bar = QLabel("Loading…")
        self._stats_bar.setStyleSheet(
            "font-size: 11px; color: #71717a; padding: 8px 24px; "
            "background: palette(alternate-base); border-bottom: 1px solid palette(mid);"
        )
        outer_layout.addWidget(self._stats_bar)

        # Scrollable cards area
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.NoFrame)

        self._cards_widget = QWidget()
        self._cards_layout = QVBoxLayout(self._cards_widget)
        self._cards_layout.setContentsMargins(24, 20, 24, 20)
        self._cards_layout.setSpacing(14)
        self._cards_layout.addStretch()

        self._scroll.setWidget(self._cards_widget)
        outer_layout.addWidget(self._scroll, 1)

        # Empty state
        self._empty_lbl = QLabel(
            "No repositories analyzed yet.\n\nEnter a GitHub URL in the Analyze tab to reverse-engineer your first codebase."
        )
        self._empty_lbl.setAlignment(Qt.AlignCenter)
        self._empty_lbl.setStyleSheet("font-size: 13px; color: #71717a; padding: 60px; line-height: 1.6;")
        self._empty_lbl.setVisible(False)
        outer_layout.addWidget(self._empty_lbl)

    def refresh(self):
        """Reloads all sessions from the database."""
        self._all_sessions = [r.to_dict() for r in self._db.get_all_sessions()]
        self._render_cards(self._all_sessions)
        count = len(self._all_sessions)
        lang_counts: dict = {}
        for s in self._all_sessions:
            lang = s.get("language", "Unknown")
            lang_counts[lang] = lang_counts.get(lang, 0) + 1
        lang_summary = ", ".join(f"{k} ({v})" for k, v in sorted(lang_counts.items(), key=lambda x: -x[1])[:5])
        self._stats_bar.setText(
            f"{count} repository session(s) persisted  ·  Languages: {lang_summary or 'N/A'}"
        )

    def _render_cards(self, sessions: list):
        # Clear existing cards
        while self._cards_layout.count() > 1:
            item = self._cards_layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()

        if not sessions:
            self._empty_lbl.setVisible(True)
            self._scroll.setVisible(False)
            return

        self._empty_lbl.setVisible(False)
        self._scroll.setVisible(True)

        for data in sessions:
            card = RepoCard(data, parent=self._cards_widget)
            card.open_requested.connect(self._on_open)
            card.reanalyze_requested.connect(self.reanalyze_requested.emit)
            card.delete_requested.connect(self._on_delete)
            card.export_requested.connect(self._on_export)
            self._cards_layout.insertWidget(self._cards_layout.count() - 1, card)

    def _filter_cards(self, query: str):
        q = query.lower().strip()
        if not q:
            filtered = self._all_sessions
        else:
            filtered = [
                s for s in self._all_sessions
                if q in s.get("repo_name", "").lower()
                or q in s.get("language", "").lower()
                or q in s.get("source_license", "").lower()
            ]
        self._render_cards(filtered)

    def _on_open(self, session_id: int):
        self.open_kb_requested.emit(session_id)

    def _on_delete(self, session_id: int, repo_name: str):
        reply = QMessageBox.question(
            self, "Delete Repository",
            f"Delete Knowledge Base for '{repo_name}'?\n\nThis cannot be undone.",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self._db.delete_session(session_id)
            self.refresh()

    def _on_export(self, session_id: int):
        rec = self._db.get_session_by_id(session_id)
        if not rec:
            return
        from app.services.exporter import export_markdown_file
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Knowledge Base", f"{rec.repo_name.replace('/', '_')}_kb.md",
            "Markdown (*.md)"
        )
        if path:
            ok = export_markdown_file(
                path,
                repo_name=rec.repo_name,
                repo_url=rec.repo_url,
                source_license=rec.source_license or "none",
                prompt_content=rec.generated_prompt or "",
            )
            if ok:
                QMessageBox.information(self, "Exported", f"Saved to:\n{path}")

    def _import_backup(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Import Git Reverse Backup", "", "JSON Backup (*.json)"
        )
        if not path:
            return
        try:
            import json
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            imported = self._db.import_sessions_from_json(data)
            QMessageBox.information(self, "Import Complete", f"Imported {imported} session(s).")
            self.refresh()
        except Exception as e:
            QMessageBox.critical(self, "Import Failed", f"Could not import backup:\n{str(e)}")
