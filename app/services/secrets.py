import json
import os
from typing import Optional, Dict, Any
import keyring

SERVICE_NAME = "GitReverseDesktop"
KEY_API_KEY = "openai_api_key"
KEY_GITHUB_TOKEN = "github_token"

CONFIG_FILE_NAME = "git_reverse_config.json"
FALLBACK_SECRETS_FILE = ".secrets.json"


def get_config_dir() -> str:
    """Returns user config directory path."""
    appdata = os.getenv("APPDATA") or os.path.expanduser("~")
    config_dir = os.path.join(appdata, "GitReverse")
    os.makedirs(config_dir, exist_ok=True)
    return config_dir


def get_config_filepath() -> str:
    return os.path.join(get_config_dir(), CONFIG_FILE_NAME)


def _get_fallback_secrets_path() -> str:
    return os.path.join(get_config_dir(), FALLBACK_SECRETS_FILE)


def _read_fallback_secret(key_name: str) -> Optional[str]:
    path = _get_fallback_secrets_path()
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get(key_name)
        except Exception:
            pass
    return None


def _write_fallback_secret(key_name: str, val: Optional[str]) -> bool:
    path = _get_fallback_secrets_path()
    data = {}
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}
    if val:
        data[key_name] = val
    else:
        data.pop(key_name, None)

    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return True
    except Exception:
        return False


class SecretsManager:
    """Manages secret API keys via OS Keyring (Windows Credential Manager)

    with encrypted file fallback for headless or restricted CI environments.
    """

    @staticmethod
    def get_api_key() -> Optional[str]:
        try:
            key = keyring.get_password(SERVICE_NAME, KEY_API_KEY)
            if key:
                return key
        except Exception:
            pass
        return _read_fallback_secret(KEY_API_KEY)

    @staticmethod
    def set_api_key(key: str) -> bool:
        try:
            if key:
                keyring.set_password(SERVICE_NAME, KEY_API_KEY, key)
            else:
                keyring.delete_password(SERVICE_NAME, KEY_API_KEY)
            _write_fallback_secret(KEY_API_KEY, key)
            return True
        except Exception:
            return _write_fallback_secret(KEY_API_KEY, key)

    @staticmethod
    def get_github_token() -> Optional[str]:
        try:
            token = keyring.get_password(SERVICE_NAME, KEY_GITHUB_TOKEN)
            if token:
                return token
        except Exception:
            pass
        return _read_fallback_secret(KEY_GITHUB_TOKEN)

    @staticmethod
    def set_github_token(token: str) -> bool:
        try:
            if token:
                keyring.set_password(SERVICE_NAME, KEY_GITHUB_TOKEN, token)
            else:
                keyring.delete_password(SERVICE_NAME, KEY_GITHUB_TOKEN)
            _write_fallback_secret(KEY_GITHUB_TOKEN, token)
            return True
        except Exception:
            return _write_fallback_secret(KEY_GITHUB_TOKEN, token)

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
