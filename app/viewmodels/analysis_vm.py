from PySide6.QtCore import QObject, Signal
from app.workers.analysis_worker import AnalysisWorker
from app.services.database import DatabaseManager


class AnalysisViewModel(QObject):
    """ViewModel managing repository analysis, worker lifecycle, and live prompt streaming.

    Extended with:
    - §48 progress_pct_updated signal (files_done, total_files)
    - §53 secrets_found signal (list of findings)
    - §59 prompt_type parameter
    """

    progress_updated = Signal(str)
    progress_pct_updated = Signal(int, int)     # §48: (files_done, total_files)
    metadata_received = Signal(dict)
    token_received = Signal(str)
    analysis_failed = Signal(str)
    analysis_completed = Signal(int, str)
    state_changed = Signal(bool)                # True = analyzing, False = idle
    secrets_found = Signal(list)                # §53: list of finding dicts

    def __init__(self, parent=None):
        super().__init__(parent)
        self.worker: AnalysisWorker = None
        self.is_analyzing = False
        self.current_prompt = ""
        self.current_meta = {}

    def start_analysis(self, repo_url: str, prompt_type: str = "Clone Prompt"):
        """Start a new analysis run.

        Args:
            repo_url: GitHub repository URL.
            prompt_type: One of 'Clone Prompt', 'Architecture Prompt',
                         'Migration Prompt', 'Documentation Prompt' (§59).
        """
        if self.is_analyzing:
            return

        self._cleanup_worker()

        self.is_analyzing = True
        self.current_prompt = ""
        self.current_meta = {}
        self.state_changed.emit(True)

        self.worker = AnalysisWorker(repo_url, prompt_type=prompt_type)
        self.worker.progress_signal.connect(self._on_progress)
        self.worker.progress_pct_signal.connect(self._on_progress_pct)          # §48
        self.worker.meta_signal.connect(self._on_meta)
        self.worker.token_signal.connect(self._on_token)
        self.worker.error_signal.connect(self._on_error)
        self.worker.finished_signal.connect(self._on_finished)
        self.worker.secrets_found_signal.connect(self._on_secrets_found)         # §53
        self.worker.start()

    def cancel_analysis(self):
        if self.worker and self.is_analyzing:
            self.worker.cancel()
            self.worker.quit()
            self.worker.wait(2000)
            self.is_analyzing = False
            self.state_changed.emit(False)

    def _cleanup_worker(self):
        """Safely stop and discard any previous worker thread."""
        if self.worker is not None:
            if self.worker.isRunning():
                self.worker.cancel()
                self.worker.quit()
                self.worker.wait(3000)
            try:
                self.worker.progress_signal.disconnect()
                self.worker.progress_pct_signal.disconnect()
                self.worker.meta_signal.disconnect()
                self.worker.token_signal.disconnect()
                self.worker.error_signal.disconnect()
                self.worker.finished_signal.disconnect()
                self.worker.secrets_found_signal.disconnect()
            except RuntimeError:
                pass
            self.worker = None

    def _on_progress(self, msg: str):
        self.progress_updated.emit(msg)

    def _on_progress_pct(self, done: int, total: int):
        self.progress_pct_updated.emit(done, total)

    def _on_meta(self, meta: dict):
        self.current_meta = meta
        self.metadata_received.emit(meta)

    def _on_token(self, token: str):
        self.current_prompt += token
        self.token_received.emit(token)

    def _on_error(self, err: str):
        self.is_analyzing = False
        self.state_changed.emit(False)
        self.analysis_failed.emit(err)

    def _on_finished(self, session_id: int, prompt: str):
        self.is_analyzing = False
        self.state_changed.emit(False)
        self.analysis_completed.emit(session_id, prompt)

    def _on_secrets_found(self, findings: list):
        self.secrets_found.emit(findings)
