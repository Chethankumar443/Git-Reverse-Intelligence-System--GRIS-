import os
import sys
import tempfile
import pytest

# Ensure project root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.github_client import validate_github_url, detect_license_type
from app.services.analyzer import CodebaseAnalyzer
from app.services.database import DatabaseManager, SessionRecord
from app.services.secrets import SecretsManager
from app.services.exporter import export_markdown_file, export_pdf_file
from app.services.llm_client import detect_provider_from_key, _is_model_free, LLMClient
from app.services.secret_scanner import scan_files, format_findings_summary
from app.services.ignore_rules import build_ignore_rules
from app.services.integrity_checker import run_full_health_check
from app.services.license_reporter import generate_license_report, classify_license


def test_github_url_validation():
    assert validate_github_url("https://github.com/torvalds/linux") == ("torvalds", "linux")
    assert validate_github_url("https://github.com/owner/repo.git") == ("owner", "repo")
    assert validate_github_url("invalid_url") is None
    assert validate_github_url("") is None


def test_license_detection():
    mit_license = "Permission is hereby granted, free of charge to any person obtaining MIT License"
    assert detect_license_type(mit_license) == "MIT"

    agpl_license = "GNU AFFERO GENERAL PUBLIC LICENSE Version 3"
    assert detect_license_type(agpl_license) == "AGPL-3.0"

    assert detect_license_type("Random text without license") == "Custom / Proprietary"


def test_codebase_analyzer():
    sample_files = {
        "main.py": "import os\nclass AppRunner:\n    pass\ndef run_main():\n    print('Hello')",
        "package.json": '{"name": "test-pkg", "dependencies": {"react": "^18.0.0", "next": "^14.0.0"}}',
        "Cargo.toml": '[dependencies]\ntokio = "1.0"\nserde = { version = "1.0" }\n',
        "go.mod": 'module example.com/test\n\ngo 1.20\n\nrequire github.com/gin-gonic/gin v1.9.0\n',
        "src/index.ts": "export interface User { name: string; }\nexport function getUser() {}",
        "requirements.txt": "fastapi>=0.100.0\nuvicorn==0.22.0\n",
        "LICENSE": "MIT License",
    }

    result = CodebaseAnalyzer.analyze(sample_files, primary_lang="Python")

    assert "Python" in result["detected_languages"] or "TypeScript" in result["detected_languages"]
    assert "React" in result["detected_frameworks"]
    assert "Next.js" in result["detected_frameworks"]
    assert len(result["entrypoints"]) > 0
    assert len(result["ast_summaries"]) > 0
    # Verify line numbers in extracted AST symbols
    assert any("line " in s for s in result["ast_summaries"])
    assert any("class AppRunner" in s and "line 2" in s for s in result["ast_summaries"])
    # Verify polyglot dependency extraction
    dep_sources = {d["source"] for d in result["dependency_details"]}
    assert "requirements.txt" in dep_sources
    assert "package.json" in dep_sources
    assert "Cargo.toml" in dep_sources
    assert "go.mod" in dep_sources


def test_database_manager():
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_file = os.path.join(tmp_dir, "test_git_reverse.db")
        db = DatabaseManager(db_path=db_file)

        # Test session creation with version tracking
        s1 = db.create_session(
            repo_url="https://github.com/owner/repo1",
            repo_name="owner/repo1",
            language="Python",
            file_count=42,
            source_license="MIT",
            commit_sha="a1b2c3d4e5f6",
            branch="main",
        )
        assert s1.id is not None
        assert s1.repo_name == "owner/repo1"

        # Test prompt update & code_symbols indexing
        symbols_str = "main.py: class AppRunner (line 2)\nsrc/index.ts: fn getUser() (line 2)"
        ok = db.update_session_prompt(s1.id, "Generated prompt text for repo1", status="complete", code_symbols=symbols_str)
        assert ok is True

        # Update again to trigger history entry
        db.update_session_prompt(s1.id, "Updated prompt text v2", status="complete", code_symbols=symbols_str)
        fetched = db.get_session_by_id(s1.id)
        assert fetched is not None
        assert fetched.generated_prompt == "Updated prompt text v2"
        assert fetched.version_number == 2
        assert "AppRunner" in fetched.code_symbols

        # Test raw symbol FTS evidence retrieval
        fts_res = db.search_fts("AppRunner")
        assert len(fts_res) == 1
        assert len(fts_res[0]["raw_symbol_matches"]) > 0
        assert "AppRunner" in fts_res[0]["raw_symbol_matches"][0]

        # Test spending log & health stats
        db.log_token_usage(500, estimated_cost_usd=0.005)
        spend = db.get_spending_summary()
        assert spend["today_tokens"] == 500
        assert spend["today_cost_usd"] == 0.005

        health = db.get_health_stats()
        assert health["session_count"] == 1

        # Test backup export / import
        export_data = db.export_all_sessions_json()
        assert "sessions" in export_data

        # Test FTS5 & LIKE search
        search_res = db.search_sessions("repo1")
        assert len(search_res) == 1
        assert search_res[0].id == s1.id

        # Test deletion
        del_ok = db.delete_session(s1.id)
        assert del_ok is True
        assert db.get_session_by_id(s1.id) is None

        db.engine.dispose()


def test_secrets_and_config():
    config = SecretsManager.load_config()
    assert "theme" in config
    assert "provider_preset" in config

    provider, base_url = detect_provider_from_key("sk-or-v1-12345")
    assert provider == "OpenRouter"
    assert "openrouter.ai" in base_url

    g_provider, g_url = detect_provider_from_key("gsk_12345")
    assert g_provider == "Groq"

    assert _is_model_free("meta-llama/llama-3.3-70b-instruct:free", "OpenRouter") is True
    assert _is_model_free("gpt-4o", "OpenAI") is False


def test_exporters():
    with tempfile.TemporaryDirectory() as tmp_dir:
        md_file = os.path.join(tmp_dir, "test_prompt.md")
        pdf_file = os.path.join(tmp_dir, "test_prompt.pdf")

        ok_md = export_markdown_file(
            filepath=md_file,
            repo_name="owner/repo",
            repo_url="https://github.com/owner/repo",
            source_license="MIT",
            prompt_content="# Recreation Prompt\nSample content",
        )
        assert ok_md is True
        assert os.path.exists(md_file)
        with open(md_file, "r", encoding="utf-8") as f:
            content = f.read()
            assert "Responsible Use" in content
            assert "MIT" in content

        ok_pdf = export_pdf_file(
            filepath=pdf_file,
            repo_name="owner/repo",
            repo_url="https://github.com/owner/repo",
            source_license="MIT",
            prompt_content="# Recreation Prompt\nSample content",
        )
        assert ok_pdf is True


def test_secret_scanner():
    files = {
        "config.py": "AWS_SECRET_KEY = 'AKIA1234567890123456'\nOPENAI_KEY = 'sk-proj-abcdef1234567890abcdef1234567890'\n",
        "main.py": "print('hello')",
    }
    findings = scan_files(files)
    assert len(findings) >= 2
    assert any("AWS" in f["pattern_type"] for f in findings)
    assert any("OpenAI" in f["pattern_type"] for f in findings)
    summary = format_findings_summary(findings)
    assert "findings" in summary.lower() or "issue" in summary.lower()


def test_ignore_rules():
    files = {
        ".gitignore": "*.log\nnode_modules/\ndist/\n",
        ".gitreverseignore": "secret.txt\n",
        "app.py": "print(1)",
        "server.log": "log error",
        "node_modules/index.js": "module",
        "secret.txt": "top secret",
    }
    rules = build_ignore_rules(files)
    filtered = rules.filter_files(files)
    assert "app.py" in filtered
    assert "server.log" not in filtered
    assert "node_modules/index.js" not in filtered
    assert "secret.txt" not in filtered


def test_integrity_checker():
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_file = os.path.join(tmp_dir, "test.db")
        db = DatabaseManager(db_path=db_file)
        report = run_full_health_check(db_file)
        assert report["overall"] in ("ok", "warning", "error")
        assert report["database"]["status"] == "ok"
        db.engine.dispose()


def test_license_reporter():
    assert classify_license("GPL-3.0") == "strong-copyleft"
    assert classify_license("LGPL-3.0") == "weak-copyleft"
    assert classify_license("MIT") == "permissive"

    report = generate_license_report(
        repo_name="owner/copyleft-project",
        repo_url="https://github.com/owner/copyleft-project",
        detected_license="GPL-3.0",
        dependency_details=[{"name": "libfoo", "version": "1.0", "license": "MIT"}],
    )

    assert report["has_copyleft"] is True
    assert report["has_strong_copyleft"] is True
    assert "report_text" in report
    assert "GPL-3.0" in report["report_text"]


def test_llm_client_stream_chat(monkeypatch):
    client = LLMClient(api_key="test_key")

    class MockDelta:
        def __init__(self, content):
            self.content = content

    class MockChoice:
        def __init__(self, content):
            self.delta = MockDelta(content)

    class MockChunk:
        def __init__(self, content):
            self.choices = [MockChoice(content)]

    def mock_create(*args, **kwargs):
        return [MockChunk("Hello "), MockChunk("world!")]

    monkeypatch.setattr(client.client.chat.completions, "create", mock_create)

    received_tokens = 0

    def token_cb(count):
        nonlocal received_tokens
        received_tokens = count

    chunks = list(client.stream_chat("sys", "user", [], ai_mode="General", token_callback=token_cb))
    assert "".join(chunks) == "Hello world!"
    assert received_tokens == 2


def test_desktop_shortcut():
    from app.services.shortcut import create_desktop_shortcut
    ok = create_desktop_shortcut("Git Reverse Test Shortcut")
    desktop_dir = os.path.join(os.path.expanduser("~"), "Desktop")
    shortcut_file = os.path.join(desktop_dir, "Git Reverse Test Shortcut.lnk")
    if ok:
        assert os.path.exists(shortcut_file)
        os.remove(shortcut_file)


