import os
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QStackedWidget, QFrame, QButtonGroup, QDialog, QCheckBox, QApplication
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPixmap
from app.viewmodels.analysis_vm import AnalysisViewModel
from app.viewmodels.session_vm import SessionViewModel
from app.viewmodels.settings_vm import SettingsViewModel
from app.views.analyze_view import AnalyzeView
from app.views.kb_view import KnowledgeBaseView
from app.views.chat_view import ChatView
from app.views.settings_view import SettingsView
from app.views.health_view import HealthView
from app.views.repo_library_view import RepoLibraryView
from app.views.styles import GEIST_LIGHT_QSS, GEIST_DARK_QSS
from app.services.secrets import SecretsManager


class AcceptableUseDialog(QDialog):
    """First-launch Responsible Use & Licensing Dialog (§6 / FR8)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Git Reverse — Responsible Use & Licensing Terms")
        self.setFixedSize(540, 380)
        self.setModal(True)
        app = QApplication.instance()
        if app:
            self.setStyleSheet(app.styleSheet())

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = QLabel("Responsible Use & Source Code Attribution Notice")
        title.setStyleSheet("font-size: 16px; font-weight: 700;")
        layout.addWidget(title)

        body_text = QLabel(
            "Git Reverse analyzes public repository structures and generates standardized AI recreation prompts.\n\n"
            "By using this application, you agree to the following responsible-use terms:\n"
            "• Source License Preservation: Generated prompts and exports will include source license attributions.\n"
            "• Responsible Development: You agree to respect original repository licenses (MIT, Apache, GPL, AGPL).\n"
            "• Educational & Reverse-Engineering Scope: For educational, architectural, and reverse-engineering research only.\n"
            "• Secrets & Privacy: Your API keys remain strictly in your local OS Credential Manager and never leave your device."
        )
        body_text.setWordWrap(True)
        body_text.setStyleSheet("font-size: 12px; line-height: 1.6; padding: 12px; border-radius: 6px;")
        layout.addWidget(body_text)

        self.chk_agree = QCheckBox("I understand and agree to preserve source license attributions.")
        self.chk_agree.setStyleSheet("font-size: 12px; font-weight: 500;")
        self.chk_agree.toggled.connect(self.on_check_toggled)
        layout.addWidget(self.chk_agree)

        btn_box = QHBoxLayout()
        btn_box.addStretch()
        self.btn_accept = QPushButton("Accept & Continue")
        self.btn_accept.setProperty("class", "g-btn-solid")
        self.btn_accept.setEnabled(False)
        self.btn_accept.clicked.connect(self.accept)
        btn_box.addWidget(self.btn_accept)
        layout.addLayout(btn_box)

    def on_check_toggled(self, checked: bool):
        self.btn_accept.setEnabled(checked)


class MainWindow(QMainWindow):
    """Git Reverse Native Desktop MainWindow Shell (PySide6 Qt6 MVVM).

    Now includes:
    - §56 Repository Library (sidebar nav item)
    - §66 First Run Wizard (shown on first launch)
    - §67 Health Center (sidebar nav item)
    - §49 Offline indicator in title bar
    """

    # Stack indices
    IDX_ANALYZE = 0
    IDX_KB = 1
    IDX_CHAT = 2
    IDX_SETTINGS = 3
    IDX_LIBRARY = 4
    IDX_HEALTH = 5

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Git Reverse — Repository Intelligence Desktop")
        self.resize(1280, 800)
        self._current_theme = "light"

        self.analysis_vm = AnalysisViewModel()
        self.session_vm = SessionViewModel()
        self.settings_vm = SettingsViewModel()

        self.init_ui()
        self.apply_theme("light")
        self.check_acceptable_use_terms()

        # Auto-apply saved theme
        config = SecretsManager.load_config()
        saved_theme = config.get("theme", "light")
        if saved_theme != "light":
            self.apply_theme(saved_theme)

        # §66 Show first-run wizard if not completed
        if not config.get("first_run_complete", False):
            self._show_first_run_wizard()

    # ── Startup Flows ─────────────────────────────────────────────────────────

    def check_acceptable_use_terms(self):
        config = SecretsManager.load_config()
        if not config.get("accepted_use_terms", False):
            dlg = AcceptableUseDialog(self)
            if dlg.exec() == QDialog.Accepted:
                config["accepted_use_terms"] = True
                SecretsManager.save_config(config)

    def _show_first_run_wizard(self):
        """§66 Shows the first-run onboarding wizard."""
        from app.views.first_run_wizard import FirstRunWizard
        wizard = FirstRunWizard(self)
        wizard.completed.connect(self._on_wizard_completed)
        wizard.exec()

    def _on_wizard_completed(self):
        # Reload settings after wizard completes
        config = SecretsManager.load_config()
        saved_theme = config.get("theme", "light")
        self.apply_theme(saved_theme)

    # ── UI ───────────────────────────────────────────────────────────────────

    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)

        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── Top Header Bar ───────────────────────────────────────────────────
        header = QFrame()
        header.setObjectName("titlebar")
        header.setFixedHeight(42)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 0, 16, 0)
        header_layout.setSpacing(8)

        # Brand Logo Icon
        logo_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".agents", "skills", "favicon (1)")
        icon_path = os.path.join(logo_dir, "favicon.ico")
        png_path = os.path.join(logo_dir, "favicon-96x96.png")

        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        if os.path.exists(png_path):
            lbl_logo = QLabel()
            pix = QPixmap(png_path).scaled(20, 20, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            lbl_logo.setPixmap(pix)
            header_layout.addWidget(lbl_logo)

        self.lbl_title = QLabel("Git Reverse")
        self.lbl_title.setObjectName("title_heading")
        self.lbl_title.setStyleSheet("font-weight: 700; font-size: 15px; letter-spacing: -0.3px;")

        self.lbl_ver = QLabel("v1.1.0")
        self.lbl_ver.setObjectName("ver_badge")

        # §49 Offline indicator
        self._offline_indicator = QLabel("Offline Mode")
        self._offline_indicator.setStyleSheet(
            "font-size: 11px; font-weight: 600; padding: 3px 10px; border-radius: 12px; "
            "background: rgba(234, 179, 8, 0.15); color: #ca8a04; border: 1px solid rgba(234, 179, 8, 0.3);"
        )
        self._offline_indicator.setVisible(False)

        # Quick Theme Toggle Button in Header
        self.btn_theme_toggle = QPushButton("Dark Mode")
        self.btn_theme_toggle.setProperty("class", "g-btn-chip")
        self.btn_theme_toggle.setCursor(Qt.PointingHandCursor)
        self.btn_theme_toggle.setFixedHeight(28)
        self.btn_theme_toggle.clicked.connect(self._toggle_quick_theme)

        header_layout.addWidget(self.lbl_title)
        header_layout.addWidget(self.lbl_ver)
        header_layout.addStretch()
        header_layout.addWidget(self._offline_indicator)
        header_layout.addWidget(self.btn_theme_toggle)
        main_layout.addWidget(header)

        # ── Body: Sidebar + Stack ─────────────────────────────────────────────
        body = QWidget()
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        # ── Sidebar ───────────────────────────────────────────────────────────
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(230)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(12, 16, 12, 16)
        sidebar_layout.setSpacing(4)

        eyebrow = QLabel("WORKSPACE")
        eyebrow.setProperty("class", "g-eyebrow")
        eyebrow.setContentsMargins(6, 0, 0, 8)
        sidebar_layout.addWidget(eyebrow)

        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)

        self.btn_analyze = QPushButton("Ingest & Analyze")
        self.btn_analyze.setCheckable(True)
        self.btn_analyze.setChecked(True)
        self.btn_analyze.setCursor(Qt.PointingHandCursor)

        self.btn_kb = QPushButton("Knowledge Base")
        self.btn_kb.setCheckable(True)
        self.btn_kb.setCursor(Qt.PointingHandCursor)

        self.btn_chat = QPushButton("Copilot Chat")
        self.btn_chat.setCheckable(True)
        self.btn_chat.setCursor(Qt.PointingHandCursor)

        self.btn_library = QPushButton("Repository Library")   # §56
        self.btn_library.setCheckable(True)
        self.btn_library.setCursor(Qt.PointingHandCursor)

        sep_lbl = QLabel("SYSTEM")
        sep_lbl.setProperty("class", "g-eyebrow")
        sep_lbl.setContentsMargins(6, 14, 0, 4)

        self.btn_health = QPushButton("Health Monitor")    # §67
        self.btn_health.setCheckable(True)
        self.btn_health.setCursor(Qt.PointingHandCursor)

        self.btn_settings = QPushButton("Settings")
        self.btn_settings.setCheckable(True)
        self.btn_settings.setCursor(Qt.PointingHandCursor)

        for btn in [self.btn_analyze, self.btn_kb, self.btn_chat,
                    self.btn_library, self.btn_health, self.btn_settings]:
            btn.setFixedHeight(40)

        self.nav_group.addButton(self.btn_analyze, self.IDX_ANALYZE)
        self.nav_group.addButton(self.btn_kb, self.IDX_KB)
        self.nav_group.addButton(self.btn_chat, self.IDX_CHAT)
        self.nav_group.addButton(self.btn_settings, self.IDX_SETTINGS)
        self.nav_group.addButton(self.btn_library, self.IDX_LIBRARY)
        self.nav_group.addButton(self.btn_health, self.IDX_HEALTH)
        self.nav_group.idClicked.connect(self.on_nav_clicked)

        sidebar_layout.addWidget(self.btn_analyze)
        sidebar_layout.addWidget(self.btn_kb)
        sidebar_layout.addWidget(self.btn_chat)
        sidebar_layout.addWidget(self.btn_library)
        sidebar_layout.addWidget(sep_lbl)
        sidebar_layout.addWidget(self.btn_health)
        sidebar_layout.addWidget(self.btn_settings)
        sidebar_layout.addStretch()

        # Sidebar Footer Card
        self.sidebar_footer = QFrame()
        self.sidebar_footer.setObjectName("sidebar_footer")
        foot_layout = QVBoxLayout(self.sidebar_footer)
        foot_layout.setContentsMargins(12, 10, 12, 10)
        foot_layout.setSpacing(4)
        lbl_arch = QLabel("Git Reverse System")
        lbl_arch.setStyleSheet("font-size: 12px; font-weight: 700;")
        lbl_sec = QLabel("● FTS5 Hybrid Engine Active")
        lbl_sec.setStyleSheet("font-size: 11px; color: #788c5d; font-weight: 600;")
        foot_layout.addWidget(lbl_arch)
        foot_layout.addWidget(lbl_sec)
        sidebar_layout.addWidget(self.sidebar_footer)

        body_layout.addWidget(sidebar)

        # ── View Stack ────────────────────────────────────────────────────────
        self.view_stack = QStackedWidget()

        self.view_analyze = AnalyzeView(self.analysis_vm)
        self.view_kb = KnowledgeBaseView(self.session_vm)
        self.view_chat = ChatView()
        self.view_settings = SettingsView(self.settings_vm)
        self.view_library = RepoLibraryView()      # §56
        self.view_health = HealthView()            # §67

        self.view_settings.theme_changed.connect(self.apply_theme)

        # ── Cross-view signal wiring ──────────────────────────────────────────
        self.view_analyze.chat_requested.connect(self.on_open_chat_for_session_id)
        self.session_vm.open_chat_requested.connect(self.on_open_chat_for_session_dict)
        # Library → KB/Analyze navigation
        self.view_library.open_kb_requested.connect(self._on_library_open_kb)
        self.view_library.reanalyze_requested.connect(self._on_library_reanalyze)

        # Stack indices must match IDX_* constants
        self.view_stack.addWidget(self.view_analyze)    # 0
        self.view_stack.addWidget(self.view_kb)         # 1
        self.view_stack.addWidget(self.view_chat)       # 2
        self.view_stack.addWidget(self.view_settings)   # 3
        self.view_stack.addWidget(self.view_library)    # 4
        self.view_stack.addWidget(self.view_health)     # 5

        body_layout.addWidget(self.view_stack, 1)
        main_layout.addWidget(body, 1)

    # ── Navigation & View Transitions ────────────────────────────────────────

    def _animate_stack_transition(self, target_idx: int):
        """Applies a smooth 150ms opacity fade-in transition when switching workspace views."""
        target_widget = self.view_stack.widget(target_idx)
        if not target_widget:
            self.view_stack.setCurrentIndex(target_idx)
            return

        from PySide6.QtWidgets import QGraphicsOpacityEffect
        from PySide6.QtCore import QPropertyAnimation, QEasingCurve

        # Set up opacity effect on target widget
        effect = QGraphicsOpacityEffect(target_widget)
        target_widget.setGraphicsEffect(effect)

        self.view_stack.setCurrentIndex(target_idx)

        anim = QPropertyAnimation(effect, b"opacity", self)
        anim.setDuration(150)
        anim.setStartValue(0.2)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        anim.finished.connect(lambda: target_widget.setGraphicsEffect(None))
        anim.start(QPropertyAnimation.DeleteWhenStopped)

    def on_nav_clicked(self, idx: int):
        self._animate_stack_transition(idx)
        if idx == self.IDX_KB:
            self.session_vm.refresh_sessions()
        elif idx == self.IDX_LIBRARY:
            self.view_library.refresh()
        elif idx == self.IDX_HEALTH:
            self.view_health.refresh()

    def on_open_chat_for_session_dict(self, s: dict):
        if s and "id" in s:
            self.on_open_chat_for_session_id(s["id"])

    def on_open_chat_for_session_id(self, session_id: int):
        self.btn_chat.setChecked(True)
        self._animate_stack_transition(self.IDX_CHAT)
        self.view_chat.select_session_by_id(session_id)

    def _on_library_open_kb(self, session_id: int):
        """Open Knowledge Base view for a specific session from the Library."""
        self.btn_kb.setChecked(True)
        self.view_stack.setCurrentIndex(self.IDX_KB)
        self.session_vm.refresh_sessions()
        # Select the session in KB view
        if hasattr(self.view_kb, "select_session_by_id"):
            self.view_kb.select_session_by_id(session_id)

    def _on_library_reanalyze(self, repo_url: str):
        """Switch to Analyze view and pre-fill the URL for re-analysis."""
        self.btn_analyze.setChecked(True)
        self.view_stack.setCurrentIndex(self.IDX_ANALYZE)
        self.view_analyze.url_input.setText(repo_url)

    # ── Theme ─────────────────────────────────────────────────────────────────

    def _force_repaint(self, widget):
        """Recursively re-polish all children so QSS property selectors re-evaluate."""
        from PySide6.QtWidgets import QWidget as _QW
        for child in widget.findChildren(_QW):
            child.style().unpolish(child)
            child.style().polish(child)
            child.update()

    def _toggle_quick_theme(self):
        new_theme = "dark" if self._current_theme == "light" else "light"
        self.apply_theme(new_theme)
        # Update saved settings
        config = SecretsManager.load_config()
        config["theme"] = new_theme
        SecretsManager.save_config(config)

    def apply_theme(self, theme: str):
        self._current_theme = theme
        if hasattr(self, "btn_theme_toggle"):
            self.btn_theme_toggle.setText("Light Mode" if theme == "dark" else "Dark Mode")
        qss = GEIST_DARK_QSS if theme == "dark" else GEIST_LIGHT_QSS

        app = QApplication.instance()
        if app:
            app.setStyleSheet("")
            app.setStyleSheet(qss)

        self.setStyleSheet("")
        self.setStyleSheet(qss)
        self._force_repaint(self)
