import os
from typing import List, Optional
from PySide6.QtCore import QObject, Signal
from app.services.database import DatabaseManager, SessionRecord
from app.services.exporter import export_markdown_file, export_pdf_file


class SessionViewModel(QObject):
    """ViewModel managing SQLite session history, search queries, session loading,

    session deletion, and PDF/Markdown export actions.
    """

    sessions_loaded = Signal(list)
    session_selected = Signal(dict)
    export_finished = Signal(bool, str)
    session_deleted = Signal(int)
    open_chat_requested = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.db_mgr = DatabaseManager()
        self.active_session: Optional[SessionRecord] = None

    def request_chat_for_active_session(self):
        if self.active_session:
            self.open_chat_requested.emit(self.active_session.to_dict())

    def refresh_sessions(self):
        records = self.db_mgr.get_all_sessions()
        session_dicts = [r.to_dict() for r in records]
        self.sessions_loaded.emit(session_dicts)

    def search_sessions(self, query: str):
        if not query.strip():
            self.refresh_sessions()
            return
        records = self.db_mgr.search_sessions(query)
        session_dicts = [r.to_dict() for r in records]
        self.sessions_loaded.emit(session_dicts)

    def select_session(self, session_id: int):
        record = self.db_mgr.get_session_by_id(session_id)
        if record:
            self.active_session = record
            self.session_selected.emit(record.to_dict())

    def delete_session(self, session_id: int):
        ok = self.db_mgr.delete_session(session_id)
        if ok:
            if self.active_session and self.active_session.id == session_id:
                self.active_session = None
            self.session_deleted.emit(session_id)
            self.refresh_sessions()

    def clear_all_history(self):
        self.db_mgr.clear_all_sessions()
        self.active_session = None
        self.refresh_sessions()

    def export_session_markdown(self, filepath: str) -> bool:
        if not self.active_session:
            self.export_finished.emit(False, "No active session selected to export.")
            return False

        success = export_markdown_file(
            filepath=filepath,
            repo_name=self.active_session.repo_name,
            repo_url=self.active_session.repo_url,
            source_license=self.active_session.source_license,
            prompt_content=self.active_session.generated_prompt,
        )
        msg = f"Exported Markdown to {filepath}" if success else "Failed to export Markdown."
        self.export_finished.emit(success, msg)
        return success

    def export_session_pdf(self, filepath: str) -> bool:
        if not self.active_session:
            self.export_finished.emit(False, "No active session selected to export.")
            return False

        success = export_pdf_file(
            filepath=filepath,
            repo_name=self.active_session.repo_name,
            repo_url=self.active_session.repo_url,
            source_license=self.active_session.source_license,
            prompt_content=self.active_session.generated_prompt,
        )
        msg = f"Exported PDF/HTML report to {filepath}" if success else "Failed to export PDF."
        self.export_finished.emit(success, msg)
        return success

    def generate_license_report(self) -> dict:
        """Generates a License Compliance Report for the active session (PRD §62)."""
        if not self.active_session:
            return {}
        from app.services.license_reporter import generate_license_report as _gen
        return _gen(
            repo_name=self.active_session.repo_name,
            repo_url=self.active_session.repo_url,
            detected_license=self.active_session.source_license or "none",
            commit_sha=getattr(self.active_session, "commit_sha", "") or "",
            branch=getattr(self.active_session, "branch", "") or "",
        )

    def get_kb_history(self) -> list:
        """Returns the KB version history list for the active session (PRD §51)."""
        if not self.active_session:
            return []
        import json
        try:
            return json.loads(self.active_session.kb_history or "[]")
        except Exception:
            return []

    def get_sessions_by_url(self, repo_url: str) -> list:
        """Returns all analysis sessions for a given repo URL (§51 multi-version tracking)."""
        records = self.db_mgr.get_sessions_by_repo_url(repo_url)
        return [r.to_dict() for r in records]
