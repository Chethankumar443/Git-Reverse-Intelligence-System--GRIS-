import os
import sys
import tempfile
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.views.components import classify_error
from app.services.database import DatabaseManager
from app.services.secrets import SecretsManager
from app.services.llm_client import LLMClient
from app.services.github_client import validate_github_url, GitHubClient


def test_error_taxonomy_classification():
    cat1 = classify_error("Invalid GitHub URL format")
    assert cat1["category"] == "Invalid input"
    assert cat1["can_retry"] is False

    cat2 = classify_error("HTTP 401 Unauthorized: Invalid API key")
    assert cat2["category"] == "Authentication failed"
    assert cat2["can_retry"] is True

    cat3 = classify_error("GitHub API rate limit reached")
    assert cat3["category"] == "Rate limited"
    assert cat3["can_retry"] is True

    cat4 = classify_error("Repository owner/repo not found on GitHub")
    assert cat4["category"] == "Resource not found"

    cat5 = classify_error("Network error connecting to GitHub: Connection refused")
    assert cat5["category"] == "Network unreachable"

    cat6 = classify_error("Unexpected KeyError: 'foo'")
    assert cat6["category"] == "Internal error"


def test_input_validation_rules():
    # GitHub URL validation
    assert validate_github_url("https://github.com/torvalds/linux") == ("torvalds", "linux")
    assert validate_github_url("file:///etc/passwd") is None
    assert validate_github_url("http://malicious.com/repo") is None
    assert validate_github_url("git@github.com:owner/repo.git") is None

    # Base URL validation helper test
    def is_valid_base_url(url: str) -> bool:
        return url.startswith("http://") or url.startswith("https://")

    assert is_valid_base_url("https://openrouter.ai/api/v1") is True
    assert is_valid_base_url("http://localhost:11434/v1") is True
    assert is_valid_base_url("ftp://invalid.com") is False
    assert is_valid_base_url("file:///tmp") is False


def test_secrets_scrubbing():
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_file = os.path.join(tmp_dir, "test_secrets.db")
        db = DatabaseManager(db_path=db_file)
        
        # Test export_all_sessions_json does NOT contain API key or GitHub token
        export_data = db.export_all_sessions_json()
        settings = export_data.get("settings", {})
        assert "api_key" not in settings
        assert "github_token" not in settings

        db.engine.dispose()

    # Test LLMClient error stream scrubbing
    client = LLMClient(api_key="sk-or-v1-secretkey123456789")
    stream = list(client.stream_recreation_prompt(
        repo_name="owner/repo",
        repo_url="https://github.com/owner/repo",
        source_license="MIT",
        languages=["Python"],
        frameworks=[],
        arch_pattern="Monolith",
        manifest_facts=[],
        file_list=["main.py"],
    ))
    full_output = "".join(stream)
    assert "sk-or-v1-secretkey123456789" not in full_output
    assert "Key Prefix:" not in full_output


def test_fts5_query_sanitization():
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_file = os.path.join(tmp_dir, "test_fts.db")
        db = DatabaseManager(db_path=db_file)
        db.create_session("https://github.com/owner/repo", "owner/repo", language="Python")
        db.update_session_prompt(1, "Sample prompt with class AppRunner", code_symbols="class AppRunner")

        # Queries with special FTS5 operators should not crash
        res1 = db.search_sessions('AppRunner OR NOT AND "')
        assert isinstance(res1, list)

        res2 = db.search_sessions('col:val * (test)')
        assert isinstance(res2, list)

        db.engine.dispose()


def test_backup_json_schema_validation():
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_file = os.path.join(tmp_dir, "test_schema.db")
        db = DatabaseManager(db_path=db_file)

        # Invalid root format
        with pytest.raises(ValueError, match="root must be a JSON object"):
            db.import_sessions_from_json(["invalid", "root"])

        # Invalid sessions field
        with pytest.raises(ValueError, match="'sessions' must be a list"):
            db.import_sessions_from_json({"sessions": "not a list"})

        # Valid empty list
        assert db.import_sessions_from_json({"sessions": []}) == 0

        db.engine.dispose()
