"""
Application Health Center — System diagnostics dashboard (PRD §67).
"""
import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QScrollArea, QFrame, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QThread
from PySide6.QtGui import QFont
from app.services.integrity_checker import run_full_health_check
from app.services.database import get_db_filepath


class _HealthWorker(QThread):
    result = Signal(dict)

    def run(self):
        try:
            db_path = get_db_filepath()
            report = run_full_health_check(db_path)
            self.result.emit(report)
        except Exception as e:
            self.result.emit({
                "overall": "error",
                "database": {"status": "error", "message": f"Health check failed: {str(e)}"},
            })


def _status_badge(status: str) -> str:
    return {"ok": "OK", "warning": "WARN", "error": "FAIL", "not_found": "N/A"}.get(status, "N/A")


def _badge_style(status: str) -> str:
    styles = {
        "ok": "background: rgba(22, 163, 74, 0.12); color: #16a34a; border: 1px solid rgba(22, 163, 74, 0.3);",
        "warning": "background: rgba(234, 179, 8, 0.12); color: #ca8a04; border: 1px solid rgba(234, 179, 8, 0.3);",
        "error": "background: rgba(220, 38, 38, 0.12); color: #dc2626; border: 1px solid rgba(220, 38, 38, 0.3);",
        "not_found": "background: palette(alternate-base); color: #71717a; border: 1px solid palette(mid);",
    }
    return styles.get(status, styles["not_found"])


class HealthView(QWidget):
    """Application Health Center — summarizes runtime, DB, Git, LLM, and storage health."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker = None
        self._init_ui()

    def _init_ui(self):
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        content = QWidget()
        scroll.setWidget(content)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        layout = QVBoxLayout(content)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(18)

        # Title row
        title_row = QHBoxLayout()
        title = QLabel("Application Health Center")
        title.setFont(QFont("Segoe UI", 18, QFont.Bold))
        title_row.addWidget(title)
        title_row.addStretch()
        self._btn_refresh = QPushButton("Refresh Diagnostics")
        self._btn_refresh.setProperty("class", "g-btn-ghost")
        self._btn_refresh.setFixedHeight(36)
        self._btn_refresh.clicked.connect(self.refresh)
        title_row.addWidget(self._btn_refresh)
        layout.addLayout(title_row)

        sub = QLabel("Real-time diagnostics for all Git Reverse system components.")
        sub.setStyleSheet("font-size: 12px; color: #71717a;")
        layout.addWidget(sub)

        # Overall status banner
        self._overall_banner = QLabel("Click Refresh to run diagnostics.")
        self._overall_banner.setWordWrap(True)
        self._overall_banner.setMinimumHeight(40)
        self._overall_banner.setAlignment(Qt.AlignVCenter)
        self._overall_banner.setStyleSheet(
            "padding: 10px 16px; border-radius: 8px; font-size: 13px; font-weight: 600; "
            + _badge_style("not_found")
        )
        layout.addWidget(self._overall_banner)

        # Health cards grid
        grp = QGroupBox("System Components")
        grp_layout = QVBoxLayout(grp)
        grp_layout.setSpacing(6)
        grp_layout.setContentsMargins(16, 18, 16, 14)

        self._rows: dict = {}
        components = [
            ("runtime", "Python Runtime"),
            ("database", "SQLite Database"),
            ("fts5", "FTS5 Search Index"),
            ("storage", "Storage Space"),
            ("git", "Git Executable"),
            ("llm_provider", "LLM Provider Key"),
        ]
        for key, label in components:
            row = QHBoxLayout()
            name_lbl = QLabel(label)
            name_lbl.setStyleSheet("font-size: 13px; font-weight: 500;")
            name_lbl.setFixedWidth(180)
            status_lbl = QLabel("—")
            status_lbl.setStyleSheet(
                "font-size: 11px; font-weight: 600; padding: 3px 10px; border-radius: 10px; "
                + _badge_style("not_found")
            )
            msg_lbl = QLabel("Not checked")
            msg_lbl.setStyleSheet("font-size: 11px; color: #71717a;")
            msg_lbl.setWordWrap(True)
            row.addWidget(name_lbl)
            row.addWidget(status_lbl)
            row.addWidget(msg_lbl, 1)
            self._rows[key] = (status_lbl, msg_lbl)
            grp_layout.addLayout(row)

        layout.addWidget(grp)

        # Stats group
        grp_stats = QGroupBox("Database Statistics")
        stats_layout = QVBoxLayout(grp_stats)
        stats_layout.setContentsMargins(16, 18, 16, 14)
        self._lbl_stats = QLabel("Run diagnostics to view stats.")
        self._lbl_stats.setStyleSheet("font-size: 12px; color: #52525b;")
        self._lbl_stats.setWordWrap(True)
        stats_layout.addWidget(self._lbl_stats)
        layout.addWidget(grp_stats)

        # Actions
        actions_row = QHBoxLayout()
        btn_clear = QPushButton("Clear Analysis Cache")
        btn_clear.setProperty("class", "g-btn-ghost")
        btn_clear.setFixedHeight(36)
        btn_clear.clicked.connect(self._clear_cache)
        actions_row.addWidget(btn_clear)
        actions_row.addStretch()
        layout.addLayout(actions_row)

        layout.addStretch()

        # Run on init
        self.refresh()

    def refresh(self):
        self._overall_banner.setText("Running diagnostics…")
        self._overall_banner.setStyleSheet(
            "padding: 10px 16px; border-radius: 8px; font-size: 13px; font-weight: 600; "
            "background: #eff6ff; color: #1d4ed8; border: 1px solid #bfdbfe;"
        )
        self._btn_refresh.setEnabled(False)
        self._worker = _HealthWorker(parent=self)
        self._worker.result.connect(self._on_result)
        self._worker.finished.connect(lambda: self._btn_refresh.setEnabled(True))
        self._worker.start()

    def _on_result(self, report: dict):
        # Runtime is always ok (we're running!)
        report["runtime"] = {
            "status": "ok",
            "message": f"Python {__import__('sys').version.split()[0]} — {__import__('platform').system()}",
        }

        overall = report.get("overall", "ok")
        if overall == "ok":
            self._overall_banner.setText("All systems operational — diagnostics healthy")
            self._overall_banner.setStyleSheet(
                "padding: 10px 16px; border-radius: 8px; font-size: 13px; font-weight: 600; "
                + _badge_style("ok")
            )
        elif overall == "warning":
            self._overall_banner.setText("Component warning — see details below")
            self._overall_banner.setStyleSheet(
                "padding: 10px 16px; border-radius: 8px; font-size: 13px; font-weight: 600; "
                + _badge_style("warning")
            )
        else:
            self._overall_banner.setText("System error detected — review details below")
            self._overall_banner.setStyleSheet(
                "padding: 10px 16px; border-radius: 8px; font-size: 13px; font-weight: 600; "
                + _badge_style("error")
            )

        for key, (status_lbl, msg_lbl) in self._rows.items():
            comp = report.get(key, {})
            status = comp.get("status", "not_found")
            msg = comp.get("message", "N/A")
            badge = _status_badge(status)
            status_lbl.setText(f"{badge}  {status.upper()}")
            status_lbl.setStyleSheet(
                "font-size: 11px; font-weight: 600; padding: 3px 10px; border-radius: 10px; "
                + _badge_style(status)
            )
            msg_lbl.setText(msg)

        # Database stats
        db_comp = report.get("database", {})
        sessions = db_comp.get("session_count", 0)
        size = db_comp.get("db_size_mb", 0.0)
        storage = report.get("storage", {})
        free_gb = storage.get("free_gb", 0.0)
        db_path = get_db_filepath()
        self._lbl_stats.setText(
            f"Sessions: {sessions}  |  DB Size: {size} MB  |  Free Disk: {free_gb} GB\n"
            f"Database path: {db_path}"
        )

    def _clear_cache(self):
        from PySide6.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self, "Clear Cache",
            "This will remove all analyzed sessions from the local database.\n\nContinue?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            from app.services.database import DatabaseManager
            db = DatabaseManager()
            db.clear_all_sessions()
            QMessageBox.information(self, "Done", "Cache cleared successfully.")
            self.refresh()
