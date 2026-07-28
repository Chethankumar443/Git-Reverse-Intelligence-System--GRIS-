import json
import os
from typing import Optional, Dict, Any
import keyring

SERVICE_NAME = "GitReverseDesktop"
KEY_API_KEY = "openai_api_key"
KEY_GITHUB_TOKEN = "github_token"

CONFIG_FILE_NAME = "git_reverse_config.json"


def get_config_dir() -> str:
    """Returns user config directory path."""
    appdata = os.getenv("APPDATA") or os.path.expanduser("~")
    config_dir = os.path.join(appdata, "GitReverse")
    os.makedirs(config_dir, exist_ok=True)
    return config_dir


def get_config_filepath() -> str:
    return os.path.join(get_config_dir(), CONFIG_FILE_NAME)


class SecretsManager:
    """Manages secret API keys via OS Keyring (Windows Credential Manager)

    and non-secret UI config via plain JSON.
    """

    @staticmethod
    def get_api_key() -> Optional[str]:
        try:
            return keyring.get_password(SERVICE_NAME, KEY_API_KEY)
        except Exception:
            return None

    @staticmethod
    def set_api_key(key: str) -> bool:
        try:
            if key:
                keyring.set_password(SERVICE_NAME, KEY_API_KEY, key)
            else:
                keyring.delete_password(SERVICE_NAME, KEY_API_KEY)
            return True
        except Exception:
            return False

    @staticmethod
    def get_github_token() -> Optional[str]:
        try:
            return keyring.get_password(SERVICE_NAME, KEY_GITHUB_TOKEN)
        except Exception:
            return None

    @staticmethod
    def set_github_token(token: str) -> bool:
        try:
            if token:
                keyring.set_password(SERVICE_NAME, KEY_GITHUB_TOKEN, token)
            else:
                keyring.delete_password(SERVICE_NAME, KEY_GITHUB_TOKEN)
            return True
        except Exception:
            return False

    @staticmethod
    def load_config() -> Dict[str, Any]:
        filepath = get_config_filepath()
        default_config = {
            "provider_preset": "OpenAI",
            "base_url": "https://api.openai.com/v1",
            "model_id": "gpt-4o",
            "theme": "light",
            "export_dir": os.path.expanduser("~/Documents"),
            # §64 Spending Protection
            "daily_spend_limit_usd": 0.0,
            "monthly_spend_limit_usd": 0.0,
            "spend_limit_action": "warn",  # "warn" or "block"
            # §61 Telemetry Policy — off by default
            "telemetry_enabled": False,
            # §66 First-run wizard
            "first_run_complete": False,
        }
        if os.path.exists(filepath):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                    default_config.update(saved)
            except Exception:
                pass
        return default_config

    @staticmethod
    def save_config(config: Dict[str, Any]) -> bool:
        filepath = get_config_filepath()
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2)
            return True
        except Exception:
            return False
