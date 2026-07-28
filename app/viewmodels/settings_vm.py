from typing import Dict, Any, List
from PySide6.QtCore import QObject, Signal, QThread
from app.services.secrets import SecretsManager
from app.services.llm_client import detect_provider_from_key, fetch_provider_models
from openai import OpenAI


class ModelFetchWorker(QThread):
    """Background worker that fetches model list from provider endpoint (non-blocking UI thread)."""

    models_ready = Signal(list, str, str, str)  # models, provider_name, base_url, error_msg

    def __init__(self, api_key: str, base_url: str, provider_name: str = "", parent=None):
        super().__init__(parent)
        self.api_key = api_key
        self.base_url = base_url
        self.provider_name = provider_name

    def run(self):
        target_key = self.api_key.strip()
        detected_name, default_url = detect_provider_from_key(target_key)
        final_provider = self.provider_name or detected_name
        target_url = self.base_url or default_url

        try:
            models_list = fetch_provider_models(target_key, target_url, final_provider)
            self.models_ready.emit(models_list, final_provider, target_url, "")
        except Exception as e:
            self.models_ready.emit([], final_provider, target_url, str(e))


class SettingsViewModel(QObject):
    """ViewModel managing secrets, provider auto-detection, and dynamic model listing."""

    settings_loaded = Signal(dict)
    key_saved = Signal(bool, str)
    key_tested = Signal(bool, str)
    models_fetched = Signal(list, str, str, str)  # models_list, provider_name, base_url, error_msg
    models_loading = Signal(bool)                 # True = fetching, False = done

    def __init__(self, parent=None):
        super().__init__(parent)
        self.config = {}
        self._fetch_worker: ModelFetchWorker = None

    def load_settings(self):
        self.config = SecretsManager.load_config()
        api_key = SecretsManager.get_api_key() or ""
        gh_token = SecretsManager.get_github_token() or ""
        payload = {
            **self.config,
            "api_key": api_key,
            "has_api_key": bool(api_key),
            "has_github_token": bool(gh_token),
        }
        self.settings_loaded.emit(payload)

        # Auto-fetch models for saved key & provider on startup
        if api_key:
            self.detect_and_fetch_models(
                key=api_key,
                base_url_override=self.config.get("base_url", ""),
                provider_override=self.config.get("provider_preset", "")
            )

    def detect_and_fetch_models(self, key: str = "", base_url_override: str = "", provider_override: str = ""):
        """Detects provider and fetches models in a background thread without altering constant selections."""
        target_key = key.strip() or SecretsManager.get_api_key() or ""
        if not target_key and "ollama" not in base_url_override.lower():
            return

        detected_name, default_url = detect_provider_from_key(target_key)
        final_provider = provider_override or self.config.get("provider_preset", "") or detected_name
        target_url = base_url_override or self.config.get("base_url", "") or default_url

        # Cancel previous worker
        if self._fetch_worker and self._fetch_worker.isRunning():
            self._fetch_worker.quit()
            self._fetch_worker.wait(500)

        self.models_loading.emit(True)
        self._fetch_worker = ModelFetchWorker(target_key, target_url, final_provider, parent=self)
        self._fetch_worker.models_ready.connect(self._on_models_ready)
        self._fetch_worker.start()

    def _on_models_ready(self, models: list, provider_name: str, base_url: str, error_msg: str):
        self.models_loading.emit(False)
        self.models_fetched.emit(models, provider_name, base_url, error_msg)

    def save_api_key(self, key: str) -> bool:
        ok = SecretsManager.set_api_key(key.strip())
        if ok and key.strip():
            saved_url = self.config.get("base_url", "")
            saved_provider = self.config.get("provider_preset", "")
            self.detect_and_fetch_models(key.strip(), saved_url, saved_provider)
        msg = "API Key saved to OS Keyring." if ok else "Failed to save API Key."
        self.key_saved.emit(ok, msg)
        return ok

    def save_github_token(self, token: str) -> bool:
        return SecretsManager.set_github_token(token.strip())

    def test_api_key(self, key: str, base_url: str, model_id: str):
        """Tests API key against provider endpoint."""
        target_key = key.strip() or SecretsManager.get_api_key()
        if not target_key and "ollama" not in base_url.lower():
            self.key_tested.emit(False, "No API Key provided to test.")
            return
        try:
            extra_headers = {}
            if "openrouter" in base_url.lower():
                extra_headers = {
                    "HTTP-Referer": "https://github.com/git-reverse/desktop",
                    "X-Title": "Git Reverse Desktop",
                }
            client = OpenAI(
                api_key=target_key or "ollama",
                base_url=base_url.rstrip("/"),
                timeout=8.0,
                default_headers=extra_headers if extra_headers else None,
            )
            res = client.models.list()
            self.key_tested.emit(True, f"Connection successful. Provider responded with {len(list(res.data))} models.")
        except Exception as e:
            self.key_tested.emit(False, f"API Key Test Failed: {str(e)}")

    def update_config(self, new_config: Dict[str, Any]) -> bool:
        self.config.update(new_config)
        return SecretsManager.save_config(self.config)
