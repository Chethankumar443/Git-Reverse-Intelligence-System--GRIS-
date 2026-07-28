from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QComboBox, QGroupBox, QFormLayout, QMessageBox, QFileDialog,
    QListWidget, QListWidgetItem, QFrame, QScrollArea, QAbstractItemView,
    QSizePolicy, QApplication
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QColor
from app.viewmodels.settings_vm import SettingsViewModel


class SettingsView(QWidget):
    """BYOK Settings View: Password-masked key entry, live provider detection,
    scrollable model list, auto-save model selection, and dynamic connection status badge."""

    theme_changed = Signal(str)

    def __init__(self, settings_vm: SettingsViewModel, parent=None):
        super().__init__(parent)
        self.vm = settings_vm
        self._all_models: list = []
        self._debounce_timer = QTimer()
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.timeout.connect(self._trigger_key_detect)
        self.init_ui()
        self.bind_vm()

    # ──────────────────────────────────────────────────────────────────────────
    # UI Build
    # ──────────────────────────────────────────────────────────────────────────

    def init_ui(self):
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        content = QWidget()
        scroll.setWidget(content)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        layout = QVBoxLayout(content)
        layout.setContentsMargins(24, 20, 24, 24)
        layout.setSpacing(16)

        title = QLabel("BYOK Model & Provider Settings")
        title.setStyleSheet("font-size: 18px; font-weight: 700;")
        layout.addWidget(title)

        sub = QLabel("Your API key is saved safely in Windows Credential Manager and is only sent to your chosen provider.")
        sub.setWordWrap(True)
        sub.setStyleSheet("font-size: 11px;")
        layout.addWidget(sub)

        # ── Section 1: API Key & Keyring Store ───────────────────────────────
        grp_key = QGroupBox("OS Credential Store & Key Detection (Windows Keyring)")
        key_layout = QVBoxLayout(grp_key)
        key_layout.setSpacing(10)
        key_layout.setContentsMargins(14, 18, 14, 14)

        # Key input row — MANDATORY PASSWORD MASKING (••••••••)
        key_row = QHBoxLayout()
        self.key_input = QLineEdit()
        self.key_input.setEchoMode(QLineEdit.Password)   # Masked as dots (••••••••)
        self.key_input.setPlaceholderText(
            "Paste OpenRouter (sk-or-v1-…), Groq (gsk_…), or OpenAI key…"
        )
        self.key_input.setMinimumHeight(36)
        self.key_input.textChanged.connect(self._on_key_changed)

        self.btn_save_key = QPushButton("Save Key")
        self.btn_save_key.setProperty("class", "g-btn-solid")
        self.btn_save_key.setFixedHeight(36)
        self.btn_save_key.clicked.connect(self.on_save_key_clicked)

        self.btn_test_key = QPushButton("Test API Key")
        self.btn_test_key.setProperty("class", "g-btn-ghost")
        self.btn_test_key.setFixedHeight(36)
        self.btn_test_key.clicked.connect(self.on_test_key_clicked)

        key_row.addWidget(self.key_input, 1)
        key_row.addWidget(self.btn_save_key)
        key_row.addWidget(self.btn_test_key)
        key_layout.addLayout(key_row)

        # Dynamic Connection Status Badge (below input)
        self.lbl_key_status = QLabel("No key configured — paste an API key above to connect")
        self.lbl_key_status.setStyleSheet(
            "font-size: 11px; font-weight: 500; padding: 6px 12px; border-radius: 6px; "
            "background-color: #fef9c3; color: #713f12; border: 1px solid #fde68a;"
        )
        self.lbl_key_status.setWordWrap(True)
        key_layout.addWidget(self.lbl_key_status)

        # GitHub token row
        gh_row = QHBoxLayout()
        self.gh_token_input = QLineEdit()
        self.gh_token_input.setEchoMode(QLineEdit.Password)
        self.gh_token_input.setPlaceholderText("ghp_… (optional, raises GitHub API limit to 5000 requests/hr)")
        self.gh_token_input.setMinimumHeight(34)
        self.btn_save_gh = QPushButton("Save Token")
        self.btn_save_gh.setProperty("class", "g-btn-ghost")
        self.btn_save_gh.setFixedHeight(34)
        self.btn_save_gh.clicked.connect(self.on_save_gh_clicked)
        gh_row.addWidget(self.gh_token_input, 1)
        gh_row.addWidget(self.btn_save_gh)

        gh_label = QLabel("GitHub Access Token (optional):")
        gh_label.setStyleSheet("font-size: 12px; font-weight: 500;")
        key_layout.addWidget(gh_label)
        key_layout.addLayout(gh_row)

        layout.addWidget(grp_key)

        # ── Section 2: LLM Provider & Dynamic Model Picker ──────────────────
        grp_model = QGroupBox("LLM Provider & Dynamic Model Picker")
        model_layout = QVBoxLayout(grp_model)
        model_layout.setSpacing(10)
        model_layout.setContentsMargins(14, 18, 14, 14)

        # Provider preset row
        prov_row = QHBoxLayout()
        prov_lbl = QLabel("Detected Provider:")
        prov_lbl.setStyleSheet("font-size: 12px; font-weight: 500;")
        prov_lbl.setFixedWidth(120)
        self.combo_preset = QComboBox()
        self.combo_preset.addItems(["OpenRouter", "Groq", "OpenAI", "DeepSeek", "Ollama Local", "Custom"])
        self.combo_preset.setMinimumHeight(34)
        self.combo_preset.currentTextChanged.connect(self.on_preset_changed)
        prov_row.addWidget(prov_lbl)
        prov_row.addWidget(self.combo_preset, 1)
        model_layout.addLayout(prov_row)

        # Base URL row
        url_row = QHBoxLayout()
        url_lbl = QLabel("Base URL:")
        url_lbl.setStyleSheet("font-size: 12px; font-weight: 500;")
        url_lbl.setFixedWidth(120)
        self.base_url_input = QLineEdit()
        self.base_url_input.setMinimumHeight(34)
        url_row.addWidget(url_lbl)
        url_row.addWidget(self.base_url_input, 1)
        model_layout.addLayout(url_row)

        # Model search filter
        search_row = QHBoxLayout()
        search_lbl = QLabel("Search Models:")
        # Active Model Indicator at TOP of Model Picker section
        self.lbl_active_model = QLabel("Active Model: gpt-4o")
        self.lbl_active_model.setStyleSheet(
            "font-size: 11px; font-weight: 600; padding: 6px 12px; border-radius: 6px; "
            "background-color: rgba(37, 99, 235, 0.1); color: #2563eb; border: 1px solid rgba(37, 99, 235, 0.3);"
        )
        model_layout.addWidget(self.lbl_active_model)

        search_row = QHBoxLayout()
        search_lbl = QLabel("Search Models:")
        search_lbl.setStyleSheet("font-size: 12px; font-weight: 500;")
        search_lbl.setFixedWidth(120)
        self.model_search = QLineEdit()
        self.model_search.setPlaceholderText("Filter model name or id…")
        self.model_search.setMinimumHeight(32)
        self.model_search.textChanged.connect(self._filter_models)
        search_row.addWidget(search_lbl)
        search_row.addWidget(self.model_search, 1)
        model_layout.addLayout(search_row)

        # Loading status indicator
        self.lbl_loading = QLabel("")
        self.lbl_loading.setStyleSheet("font-size: 11px; color: #0070f3; font-weight: 500;")
        model_layout.addWidget(self.lbl_loading)

        # Models header
        models_header = QHBoxLayout()
        self.lbl_models_count = QLabel("Available Models")
        self.lbl_models_count.setStyleSheet("font-size: 12px; font-weight: 700;")
        self.lbl_free_badge = QLabel("")
        self.lbl_free_badge.setStyleSheet(
            "font-size: 10px; font-weight: 600; padding: 2px 8px; "
            "border-radius: 10px; background-color: #dcfce7; color: #166534;"
        )
        models_header.addWidget(self.lbl_models_count)
        models_header.addWidget(self.lbl_free_badge)
        models_header.addStretch()
        model_layout.addLayout(models_header)

        # Scrollable QListWidget listing ALL models dynamically
        self.model_list = QListWidget()
        self.model_list.setMinimumHeight(220)
        self.model_list.setMaximumHeight(320)
        self.model_list.setAlternatingRowColors(True)
        self.model_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self.model_list.itemClicked.connect(self.on_model_selected)
        self.model_list.itemSelectionChanged.connect(self._on_model_item_selection_changed)
        model_layout.addWidget(self.model_list)

        hint = QLabel("Hint: Click any model above to select and activate it instantly for all AI analyses.")
        hint.setStyleSheet("font-size: 11px; color: #71717a;")
        model_layout.addWidget(hint)

        layout.addWidget(grp_model)

        # ── Section 3: Appearance & Export ──────────────────────────────────
        grp_app = QGroupBox("Appearance & Default Export Directory")
        app_layout = QVBoxLayout(grp_app)
        app_layout.setSpacing(10)
        app_layout.setContentsMargins(14, 18, 14, 14)

        theme_row = QHBoxLayout()
        theme_lbl = QLabel("Theme:")
        theme_lbl.setStyleSheet("font-size: 12px; font-weight: 500;")
        theme_lbl.setFixedWidth(120)
        self.combo_theme = QComboBox()
        self.combo_theme.addItems(["light", "dark"])
        self.combo_theme.setMinimumHeight(34)
        self.combo_theme.currentTextChanged.connect(self.on_theme_changed)
        theme_row.addWidget(theme_lbl)
        theme_row.addWidget(self.combo_theme, 1)
        app_layout.addLayout(theme_row)

        dir_row = QHBoxLayout()
        dir_lbl = QLabel("Export Directory:")
        dir_lbl.setStyleSheet("font-size: 12px; font-weight: 500;")
        dir_lbl.setFixedWidth(120)
        self.export_dir_input = QLineEdit()
        self.export_dir_input.setMinimumHeight(34)
        self.btn_browse = QPushButton("Browse…")
        self.btn_browse.setProperty("class", "g-btn-ghost")
        self.btn_browse.clicked.connect(self.on_browse_clicked)
        dir_row.addWidget(dir_lbl)
        dir_row.addWidget(self.export_dir_input, 1)
        dir_row.addWidget(self.btn_browse)
        app_layout.addLayout(dir_row)

        layout.addWidget(grp_app)

        # Save Button
        save_row = QHBoxLayout()
        save_row.addStretch()
        self.btn_save = QPushButton("Save Preferences")
        self.btn_save.setProperty("class", "g-btn-solid")
        self.btn_save.setFixedHeight(38)
        self.btn_save.setMinimumWidth(160)
        self.btn_save.clicked.connect(self.on_save_config_clicked)
        save_row.addWidget(self.btn_save)
        layout.addLayout(save_row)

        # ── §64 Spending Protection ───────────────────────────────────────────
        grp_spend = QGroupBox("Spending Protection (§64)")
        spend_layout = QFormLayout(grp_spend)
        spend_layout.setSpacing(8)

        self.daily_limit_input = QLineEdit()
        self.daily_limit_input.setPlaceholderText("0.00 (0 = disabled)")
        self.daily_limit_input.setMaximumWidth(120)
        spend_layout.addRow("Daily Spend Limit (USD):", self.daily_limit_input)

        self.monthly_limit_input = QLineEdit()
        self.monthly_limit_input.setPlaceholderText("0.00 (0 = disabled)")
        self.monthly_limit_input.setMaximumWidth(120)
        spend_layout.addRow("Monthly Spend Limit (USD):", self.monthly_limit_input)

        self.combo_limit_action = QComboBox()
        self.combo_limit_action.addItems(["warn", "block"])
        self.combo_limit_action.setMaximumWidth(120)
        spend_layout.addRow("On Limit Reached:", self.combo_limit_action)

        spend_note = QLabel("'warn' shows a banner. 'block' prevents new LLM calls for the day/month.")
        spend_note.setWordWrap(True)
        spend_note.setStyleSheet("font-size: 11px; color: #71717a;")
        spend_layout.addRow(spend_note)

        # Spending Summary
        self._lbl_spend_summary = QLabel("Loading spending summary…")
        self._lbl_spend_summary.setStyleSheet(
            "font-size: 11px; padding: 8px; border-radius: 6px; "
            "background: #fafafa; border: 1px solid #e4e4e7;"
        )
        self._lbl_spend_summary.setWordWrap(True)
        spend_layout.addRow("Today / Month / Total:", self._lbl_spend_summary)
        self._refresh_spending_summary()

        layout.addWidget(grp_spend)

        # ── §65 Backup & Restore ──────────────────────────────────────────────
        grp_backup = QGroupBox("Backup & Restore (§65)")
        backup_layout = QHBoxLayout(grp_backup)
        backup_layout.setSpacing(8)

        btn_export_json = QPushButton("Export All Sessions (JSON)")
        btn_export_json.setProperty("class", "g-btn-ghost")
        btn_export_json.clicked.connect(self._on_export_backup)
        backup_layout.addWidget(btn_export_json)

        btn_import_json = QPushButton("Import Backup…")
        btn_import_json.setProperty("class", "g-btn-ghost")
        btn_import_json.clicked.connect(self._on_import_backup)
        backup_layout.addWidget(btn_import_json)

        backup_layout.addStretch()
        layout.addWidget(grp_backup)


    # ──────────────────────────────────────────────────────────────────────────
    # Bindings & VM Callbacks
    # ──────────────────────────────────────────────────────────────────────────

    def bind_vm(self):
        self.vm.settings_loaded.connect(self.on_settings_loaded)
        self.vm.key_saved.connect(self.on_key_saved)
        self.vm.key_tested.connect(self.on_key_tested)
        self.vm.models_fetched.connect(self.on_models_fetched)
        self.vm.models_loading.connect(self.on_models_loading)
        self.vm.load_settings()

    def on_settings_loaded(self, config: dict):
        self.base_url_input.setText(config.get("base_url", "https://openrouter.ai/api/v1"))
        self.export_dir_input.setText(config.get("export_dir", ""))

        self.combo_theme.blockSignals(True)
        self.combo_theme.setCurrentText(config.get("theme", "light"))
        self.combo_theme.blockSignals(False)

        self.combo_preset.blockSignals(True)
        self.combo_preset.setCurrentText(config.get("provider_preset", "OpenRouter"))
        self.combo_preset.blockSignals(False)

        saved_model = config.get("model_id", "gpt-4o")
        if saved_model:
            self.lbl_active_model.setText(f"Active Model: {saved_model}")

        # §64 Spending limits
        if hasattr(self, 'daily_limit_input'):
            self.daily_limit_input.setText(str(config.get("daily_spend_limit_usd", 0.0)))
            self.monthly_limit_input.setText(str(config.get("monthly_spend_limit_usd", 0.0)))
            action = config.get("spend_limit_action", "warn")
            self.combo_limit_action.setCurrentText(action)

        # Populate Key Input with Masked Password Dots (••••••••) if API key exists
        api_key = config.get("api_key", "")
        if api_key:
            self.key_input.blockSignals(True)
            self.key_input.setText(api_key)  # Password echo mode renders as dots (••••••••)
            self.key_input.blockSignals(False)
            self._set_status_connected("API Key loaded from Windows Keyring — fetching models…")
        elif config.get("has_api_key"):
            self._set_status_connected("API Key stored in Windows Keyring")

        if config.get("has_github_token"):
            self.gh_token_input.setPlaceholderText("GitHub Token: Saved in Keyring  ghp_…")

    def on_models_loading(self, loading: bool):
        if loading:
            self.lbl_loading.setText("Connecting & fetching model list from provider…")
            self.model_list.setEnabled(False)
        else:
            self.lbl_loading.setText("")
            self.model_list.setEnabled(True)

    def on_models_fetched(self, models: list, provider_name: str, base_url: str, error_msg: str):
        if error_msg:
            self._set_status_error(f"Failed to connect to {provider_name}: {error_msg}")
            return

        self._all_models = models

        # Keep provider selection constant based on user config/preset
        active_provider = self.vm.config.get("provider_preset", provider_name)
        self.combo_preset.blockSignals(True)
        self.combo_preset.setCurrentText(active_provider)
        self.combo_preset.blockSignals(False)

        free_count = sum(1 for m in models if m["is_free"])
        total = len(models)

        self.lbl_models_count.setText(f"Available Models ({total})")
        self.lbl_free_badge.setText(f"{free_count} FREE")
        self.lbl_free_badge.setVisible(free_count > 0)

        # Populate QListWidget
        saved_model = self.vm.config.get("model_id", "gpt-4o")
        self._populate_list(models, saved_model)

        # Dynamic connection status badge (below the API key input)
        self._set_status_connected(
            f"Detected Provider: {active_provider} | Loaded {total} models ({free_count} free)"
        )

    # ──────────────────────────────────────────────────────────────────────────
    # Model List & Search Helpers
    # ──────────────────────────────────────────────────────────────────────────

    def _populate_list(self, models: list, active_model_id: str = ""):
        self.model_list.clear()
        for m in models:
            item = QListWidgetItem()
            item.setText(m["display_name"])
            item.setData(Qt.UserRole, m["id"])
            if m["is_free"]:
                item.setForeground(QColor("#166534"))  # Green text for free models
            self.model_list.addItem(item)

        if active_model_id:
            self._highlight_active(active_model_id)

    def _highlight_active(self, model_id: str):
        for i in range(self.model_list.count()):
            item = self.model_list.item(i)
            if item.data(Qt.UserRole) == model_id or item.text().replace("[FREE] ", "") == model_id:
                self.model_list.setCurrentItem(item)
                self.model_list.scrollToItem(item, QAbstractItemView.PositionAtCenter)
                break

    def _filter_models(self, query: str):
        q = query.lower().strip()
        for i in range(self.model_list.count()):
            item = self.model_list.item(i)
            item.setHidden(q != "" and q not in item.text().lower())

    # ──────────────────────────────────────────────────────────────────────────
    # Key Detection & Status Badge Helpers
    # ──────────────────────────────────────────────────────────────────────────

    def _on_key_changed(self, text: str):
        if len(text.strip()) >= 10:
            self._debounce_timer.start(800)

    def _trigger_key_detect(self):
        key = self.key_input.text().strip()
        if key:
            from app.services.llm_client import detect_provider_from_key
            detected_provider, default_url = detect_provider_from_key(key)
            self.combo_preset.blockSignals(True)
            self.combo_preset.setCurrentText(detected_provider)
            self.combo_preset.blockSignals(False)
            self.base_url_input.setText(default_url)
            self.vm.update_config({
                "provider_preset": detected_provider,
                "base_url": default_url,
            })
            self.vm.detect_and_fetch_models(key, base_url_override=default_url, provider_override=detected_provider)

    def _set_status_testing(self, msg: str = "Testing connection..."):
        self.lbl_key_status.setText(f"⏳  {msg}")
        self.lbl_key_status.setStyleSheet(
            "font-size: 11px; font-weight: 600; padding: 6px 12px; border-radius: 6px; "
            "background-color: #fef9c3; color: #854d0e; border: 1px solid #fde047;"
        )

    def _set_status_connected(self, msg: str):
        self.lbl_key_status.setText(f"✓  {msg}")
        self.lbl_key_status.setStyleSheet(
            "font-size: 11px; font-weight: 600; padding: 6px 12px; border-radius: 6px; "
            "background-color: #dcfce7; color: #166534; border: 1px solid #86efac;"
        )

    def _set_status_error(self, msg: str):
        self.lbl_key_status.setText(f"✗  {msg}")
        self.lbl_key_status.setStyleSheet(
            "font-size: 11px; font-weight: 600; padding: 6px 12px; border-radius: 6px; "
            "background-color: #fee2e2; color: #991b1b; border: 1px solid #fca5a5;"
        )

    # ──────────────────────────────────────────────────────────────────────────
    # Permanent Model Selection & Auto-Save
    # ──────────────────────────────────────────────────────────────────────────

    def _on_model_item_selection_changed(self):
        items = self.model_list.selectedItems()
        if items:
            self.on_model_selected(items[0])

    def on_model_selected(self, item: QListWidgetItem):
        raw_id = item.data(Qt.UserRole) or item.text()
        clean_model_id = raw_id.replace("[FREE] ", "").strip()
        display_name = item.text()

        self.lbl_active_model.setText(f"✓ Active Model: {display_name}")
        self.lbl_active_model.setStyleSheet(
            "font-size: 11px; font-weight: 600; padding: 6px 12px; border-radius: 6px; "
            "background-color: rgba(22, 163, 74, 0.12); color: #16a34a; border: 1px solid rgba(22, 163, 74, 0.3);"
        )

        # Permanent configuration update — all future LLM calls use this selected model
        self.vm.update_config({
            "model_id": clean_model_id,
            "provider_preset": self.combo_preset.currentText(),
            "base_url": self.base_url_input.text().strip(),
        })

    # ──────────────────────────────────────────────────────────────────────────
    # Handlers
    # ──────────────────────────────────────────────────────────────────────────

    def on_preset_changed(self, preset: str):
        presets = {
            "OpenRouter": "https://openrouter.ai/api/v1",
            "Groq": "https://api.groq.com/openai/v1",
            "OpenAI": "https://api.openai.com/v1",
            "DeepSeek": "https://api.deepseek.com/v1",
            "Ollama Local": "http://localhost:11434/v1",
        }
        if preset in presets:
            new_url = presets[preset]
            self.base_url_input.setText(new_url)
            self.vm.update_config({
                "provider_preset": preset,
                "base_url": new_url,
            })
            key = self.key_input.text().strip() or ""
            self.vm.detect_and_fetch_models(key, base_url_override=new_url, provider_override=preset)

    def on_save_key_clicked(self):
        key = self.key_input.text().strip()
        if not key:
            self._set_status_error("API key field is empty.")
            return
        self.vm.save_api_key(key)

    def on_save_gh_clicked(self):
        token = self.gh_token_input.text().strip()
        if not token:
            return
        self.vm.save_github_token(token)
        QMessageBox.information(self, "Saved", "GitHub Access Token saved to Keyring.")
        self.gh_token_input.clear()
        self.gh_token_input.setPlaceholderText("GitHub Token: Saved in Keyring  ghp_…")

    def on_test_key_clicked(self):
        self._set_status_testing("Testing API Key connection...")
        key = self.key_input.text().strip()
        base_url = self.base_url_input.text().strip()
        item = self.model_list.currentItem()
        model_id = item.data(Qt.UserRole) if item else "gpt-4o"
        self.vm.test_api_key(key, base_url, model_id)

    def on_key_saved(self, ok: bool, msg: str):
        if ok:
            self._set_status_connected("API Key saved to Windows Keyring")
        else:
            self._set_status_error(f"Save failed: {msg}")

    def on_key_tested(self, ok: bool, msg: str):
        if ok:
            self._set_status_connected(msg)
        else:
            self._set_status_error(msg)

    def on_theme_changed(self, theme: str):
        self.theme_changed.emit(theme)

    def on_browse_clicked(self):
        d = QFileDialog.getExistingDirectory(self, "Select Export Directory")
        if d:
            self.export_dir_input.setText(d)

    def on_save_config_clicked(self):
        item = self.model_list.currentItem()
        model_id = item.data(Qt.UserRole) if item else self.vm.config.get("model_id", "gpt-4o")
        clean_model = model_id.replace("[FREE] ", "").strip()
        try:
            daily_limit = float(self.daily_limit_input.text().strip() or 0)
        except ValueError:
            daily_limit = 0.0
        try:
            monthly_limit = float(self.monthly_limit_input.text().strip() or 0)
        except ValueError:
            monthly_limit = 0.0

        new_config = {
            "provider_preset": self.combo_preset.currentText(),
            "base_url": self.base_url_input.text().strip(),
            "model_id": clean_model,
            "theme": self.combo_theme.currentText(),
            "export_dir": self.export_dir_input.text().strip(),
            # §64
            "daily_spend_limit_usd": daily_limit,
            "monthly_spend_limit_usd": monthly_limit,
            "spend_limit_action": self.combo_limit_action.currentText(),
        }
        self.vm.update_config(new_config)
        self.lbl_active_model.setText(f"Active Model: {clean_model}")
        QMessageBox.information(self, "Saved", f"Preferences saved.\nActive Model: {clean_model}")

    def _refresh_spending_summary(self):
        """Display spending totals from DatabaseManager (§64)."""
        try:
            from app.services.database import DatabaseManager
            db = DatabaseManager()
            s = db.get_spending_summary()
            self._lbl_spend_summary.setText(
                f"Today: ${s['today_cost_usd']} ({s['today_tokens']} tokens)  ·  "
                f"Month: ${s['month_cost_usd']} ({s['month_tokens']} tokens)  ·  "
                f"All-time: ${s['total_cost_usd']}"
            )
        except Exception:
            self._lbl_spend_summary.setText("Unable to load spending data.")

    def _on_export_backup(self):
        """Export all sessions as a JSON backup file (§65)."""
        from app.services.database import DatabaseManager
        import json
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Backup", "git_reverse_backup.json", "JSON (*.json)"
        )
        if not path:
            return
        try:
            db = DatabaseManager()
            data = db.export_all_sessions_json()
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)
            QMessageBox.information(self, "Backup Exported", f"Backup saved to:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Export Failed", str(e))

    def _on_import_backup(self):
        """Import sessions from a JSON backup file (§65)."""
        from app.services.database import DatabaseManager
        import json
        path, _ = QFileDialog.getOpenFileName(
            self, "Import Backup", "", "JSON Backup (*.json)"
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            db = DatabaseManager()
            count = db.import_sessions_from_json(data)
            QMessageBox.information(self, "Import Complete", f"Imported {count} session(s).")
        except Exception as e:
            QMessageBox.critical(self, "Import Failed", str(e))
