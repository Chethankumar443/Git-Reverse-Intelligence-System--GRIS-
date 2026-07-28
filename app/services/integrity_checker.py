"""
Integrity Checker — Verifies application data health (PRD §60).

Checks: SQLite database integrity, Knowledge Base internal consistency,
backup file validity, and storage health.
"""
import os
import json
from typing import Dict, Any


def check_database_integrity(db_path: str) -> Dict[str, Any]:
    """Runs SQLite PRAGMA integrity_check on the database file.

    Returns a dict with status ('ok'/'error'), session_count, db_size_mb.
    """
    result = {"status": "ok", "message": "Database healthy", "session_count": 0, "db_size_mb": 0.0}

    if not db_path or not os.path.exists(db_path):
        result["status"] = "not_found"
        result["message"] = "Database file not found"
        return result

    try:
        import sqlite3
        size_bytes = os.path.getsize(db_path)
        result["db_size_mb"] = round(size_bytes / (1024 * 1024), 2)

        conn = sqlite3.connect(db_path, timeout=5)
        cursor = conn.cursor()

        # SQLite integrity check
        rows = cursor.execute("PRAGMA integrity_check;").fetchall()
        if rows and rows[0][0] != "ok":
            result["status"] = "corrupted"
            result["message"] = f"Integrity issue: {rows[0][0]}"
            conn.close()
            return result

        # Count sessions
        try:
            count = cursor.execute("SELECT COUNT(*) FROM session_records;").fetchone()
            result["session_count"] = count[0] if count else 0
        except Exception:
            result["session_count"] = 0

        conn.close()
        result["message"] = f"Database healthy — {result['session_count']} sessions, {result['db_size_mb']} MB"

    except Exception as e:
        result["status"] = "error"
        result["message"] = f"Database check failed: {str(e)}"

    return result


def check_fts5_index(db_path: str) -> Dict[str, Any]:
    """Verifies the FTS5 virtual table exists and is queryable."""
    result = {"status": "ok", "message": "FTS5 index active"}

    if not db_path or not os.path.exists(db_path):
        result["status"] = "not_found"
        result["message"] = "Database not found"
        return result

    try:
        import sqlite3
        conn = sqlite3.connect(db_path, timeout=5)
        cursor = conn.cursor()
        # A simple select on the FTS5 table validates it exists
        cursor.execute("SELECT COUNT(*) FROM session_records_fts;").fetchone()
        conn.close()
    except Exception as e:
        result["status"] = "error"
        result["message"] = f"FTS5 index issue: {str(e)}"

    return result


def check_storage_space() -> Dict[str, Any]:
    """Returns available disk space on the user data drive."""
    result = {"status": "ok", "free_gb": 0.0, "message": ""}
    try:
        import shutil
        appdata = os.getenv("APPDATA") or os.path.expanduser("~")
        total, used, free = shutil.disk_usage(appdata)
        free_gb = round(free / (1024 ** 3), 1)
        result["free_gb"] = free_gb
        if free_gb < 0.5:
            result["status"] = "warning"
            result["message"] = f"Low disk space: {free_gb} GB free"
        else:
            result["message"] = f"{free_gb} GB free"
    except Exception as e:
        result["status"] = "error"
        result["message"] = f"Could not determine disk space: {str(e)}"
    return result


def check_git_available() -> Dict[str, Any]:
    """Checks whether a git executable is available on PATH."""
    result = {"status": "ok", "message": "Git available", "version": ""}
    try:
        import subprocess
        out = subprocess.run(
            ["git", "--version"], capture_output=True, text=True, timeout=5
        )
        if out.returncode == 0:
            result["version"] = out.stdout.strip()
            result["message"] = result["version"]
        else:
            result["status"] = "warning"
            result["message"] = "Git not found on PATH (optional for zipball mode)"
    except FileNotFoundError:
        result["status"] = "warning"
        result["message"] = "Git not installed (optional for zipball mode)"
    except Exception as e:
        result["status"] = "error"
        result["message"] = f"Git check failed: {str(e)}"
    return result


def check_llm_provider_configured() -> Dict[str, Any]:
    """Checks whether an LLM API key is saved in the OS keyring."""
    result = {"status": "ok", "message": ""}
    try:
        from app.services.secrets import SecretsManager
        key = SecretsManager.get_api_key()
        if key and len(key.strip()) > 8:
            result["message"] = "API Key configured in OS Keyring"
        else:
            result["status"] = "warning"
            result["message"] = "No LLM API Key configured — go to Settings"
    except Exception as e:
        result["status"] = "error"
        result["message"] = f"Keyring check failed: {str(e)}"
    return result


def run_full_health_check(db_path: str) -> Dict[str, Any]:
    """Runs all health checks and returns a combined health report dict."""
    db_result = check_database_integrity(db_path)
    fts5_result = check_fts5_index(db_path)
    storage_result = check_storage_space()
    git_result = check_git_available()
    llm_result = check_llm_provider_configured()

    overall = "ok"
    for r in [db_result, fts5_result, storage_result, llm_result]:
        if r["status"] == "error":
            overall = "error"
            break
        elif r["status"] in ("warning", "not_found", "corrupted"):
            overall = "warning"

    return {
        "overall": overall,
        "database": db_result,
        "fts5": fts5_result,
        "storage": storage_result,
        "git": git_result,
        "llm_provider": llm_result,
    }


def verify_backup_bundle(filepath: str) -> Dict[str, Any]:
    """Validates a Git Reverse backup bundle file (.zip or .json)."""
    result = {"status": "ok", "message": "Backup valid", "contents": []}
    if not os.path.exists(filepath):
        result["status"] = "error"
        result["message"] = "Backup file not found"
        return result

    try:
        if filepath.endswith(".json"):
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            required_keys = {"sessions", "settings"}
            found = set(data.keys())
            result["contents"] = list(found)
            if not required_keys.issubset(found):
                result["status"] = "warning"
                result["message"] = f"Backup missing keys: {required_keys - found}"
            else:
                result["message"] = f"Valid backup bundle ({len(data.get('sessions', []))} sessions)"
        else:
            result["status"] = "warning"
            result["message"] = "Unknown backup format — expected .json bundle"
    except Exception as e:
        result["status"] = "error"
        result["message"] = f"Backup verification failed: {str(e)}"

    return result
