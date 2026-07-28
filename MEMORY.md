# Git Reverse — Project Memory & History

## Project Overview
Git Reverse is a native desktop intelligence platform that ingests GitHub repository URLs, analyzes their code structures, dependency trees, and architecture patterns, stores extracted facts in a local SQLite database (FTS5 enabled), and generates standardized AI recreation prompts and interactive Q&A responses via a BYOK (Bring Your Own Key) model.

## Documentation Index
- `prd.md` — Product Requirements (PRD v1.1: 70 sections covering AI reliability, confidence scoring, secret scanning, license compliance, offline mode, version tracking, Health Center)
- `trd.md` — Technical Requirements (TRD v1.0: System Architecture Document v1.3 resolution, protocol specs, database schemas, IPC)
- `DESIGN-vercel.md` — Vercel Geist Design System Spec (Stark ink/canvas palette, Geist Sans display, Geist Mono eyebrows, hairline cards, desktop ergonomics)
- `implementation_plan.md` — Active Implementation Plan & Traceability Matrix
- `walkthrough.md` — Verification & Execution Walkthrough
- `git_reverse.spec` — PyInstaller standalone executable bundling specification
- `.agents/` — Custom design skills and frontend guidance

## Key Architectural Decisions & Requirements
1. **Desktop Native Architecture**:
   - Single `.exe` Windows installation with zero console windows (`US1`, `trd.md §9`).
   - High information density with desktop ergonomics (frameless header, sidebar navigation, compact split-pane workspace).
2. **Local-First & Privacy**:
   - Shallow clone & analysis stored locally in SQLite (`WAL` mode).
   - Local Secret Scanner (`secret_scanner.py` — §53) detects 24 credential rule families before AI transmission.
   - Secrets stored exclusively in OS Credential Manager (`keyring`).
3. **Responsible-Use Policy**:
   - License detection for 20+ open-source and proprietary licenses (`FR8`, `US9`).
   - Full License Compliance breakdown generator (`license_reporter.py` — §62).
   - Mandatory attribution header/footer appended to all PDF and Markdown prompt exports.
   - Mandatory first-launch Acceptable Use acceptance dialog and 5-step onboarding wizard.

## Change Log & Milestones
- **2026-07-27**:
  - **Full PRD v1.1 & TRD v1.0 Feature Implementation**:
    - Built `secret_scanner.py` (§53): Local secret scanner detecting 24 rule families (AWS, GitHub, Stripe, OpenAI, JWT, Slack, private keys) before AI transmission.
    - Built `ignore_rules.py` (§54): `.gitignore` & `.gitreverseignore` path parser.
    - Built `integrity_checker.py` (§67): System Health Center diagnostics covering SQLite DB, FTS5 index, free storage, Git executable, and LLM key connectivity.
    - Built `license_reporter.py` (§62): Full SPDX license compliance breakdown and copyleft obligation analysis generator.
    - Built `repo_library_view.py` (§56): Repository Library home base supporting session search, version tracking (§51), JSON backup import/export, and session management.
    - Built `health_view.py` (§67): Real-time application diagnostics center dashboard.
  - **First-Run Wizard Overhaul (`first_run_wizard.py`)**:
    - 5-step onboarding wizard (`Welcome`, `Provider`, `Test`, `Storage`, `Ready`) with step progress bar.
    - 2x2 enterprise feature card grid replacing emoji bullet lists.
    - Integrated live API connectivity testing (`LLMClient.test_connection()`) with async `_TestWorker`.
  - **HTTP 402 Credit & Token Request Capping (`llm_client.py`)**:
    - Added explicit `max_tokens=4096` token request cap to prevent OpenRouter/LLM providers from rejecting queries on accounts with limited credits.
    - Added dedicated HTTP 402 exception handling in both streaming completion and connection testing, with structured suggestions to switch to free-tier models (`:free`) or add credits.
  - **Complete Vercel Geist Enterprise UI/UX Overhaul**:
    - Aligned stylesheet (`styles.py`) and all views (`main_window.py`, `analyze_view.py`, `kb_view.py`, `chat_view.py`, `repo_library_view.py`, `health_view.py`, `settings_view.py`) with `DESIGN-vercel.md`.
    - Prominent 2x2 Metadata Grid at top of `AnalyzeView` left pane displaying Source License, Indexed Files, Stack, Pattern, and Commit SHA.
    - Removed all cheap emojis across all sidebar buttons, titlebars, cards, and status banners.
    - Fixed `QListWidget::item:selected` highlight styling in `SettingsView` (high-contrast `#2563eb` selection background with white text).
    - Auto-activation and instant save on model click in settings.
    - Cleaned titlebar by removing `● SQLite WAL FTS5 Active` text.
  - **Automated Verification**:
    - 10/10 unit & service tests passing in `pytest` (`test_backend.py`).
    - Fixed Ruby fallback warning via root `.ruby-version` file.

- **2026-07-24**:
  - Cleaned workspace (retained `.agents` and `DESIGN-vercel.md`).
  - Added distilled `prd.md` and `trd.md`.
  - Initialized `MEMORY.md` tracking log.
  - Created `implementation_plan.md` artifact.
  - Installed Python 3.12 dependencies (`PySide6 6.11.1`, `openai`, `requests`, `SQLAlchemy`, `keyring`, `Jinja2`, `PyInstaller 6.21.0`).
  - Implemented core services: `secrets.py`, `database.py`, `github_client.py`, `analyzer.py`, `llm_client.py`, `exporter.py`.
  - Implemented background worker `analysis_worker.py` (QThread execution).
  - Implemented ViewModels (`analysis_vm.py`, `session_vm.py`, `settings_vm.py`).
  - Implemented Vercel Geist Qt QSS stylesheet (`styles.py`) and Views (`analyze_view.py`, `kb_view.py`, `chat_view.py`, `settings_view.py`, `main_window.py`).
  - Added mandatory first-launch Responsible Use Acceptance dialog (`AcceptableUseDialog`).
  - Built application entrypoint `main.py` and PyInstaller packaging configuration (`git_reverse.spec`).
  - **Dynamic BYOK Key & Model Detection**:
    - Automatically detects provider (`OpenRouter`, `Groq`, `OpenAI`, `DeepSeek`) from key prefix (`sk-or-v1-`, `gsk_`, `sk-`).
    - Uses OpenAI SDK `client.models.list()` to fetch provider models dynamically.
    - Tags free-tier models with `[FREE]` prefix in green.
  - **Comprehensive UI/UX & Dark Mode Theme Fixes**:
    - Converted Qt QSS rules in `styles.py` to proper property selectors (`QFrame[class="g-pane"]`, `QLabel[class="g-eyebrow"]`, `QPushButton[class="g-btn-chip"]`).
    - Added `_force_repaint()` helper to recursively unpolish and re-polish widgets during theme toggling.
    - Fixed dark mode sidebar contrast (`nav_muted: #d4d4d8`).
  - **Settings UI & Security Enhancements**:
    - API Key input masked (`QLineEdit.Password`).
    - Added connection status badge (green for connected, red for error, yellow for unconfigured).
    - Replaced model dropdown with a scrollable `QListWidget` supporting 300+ models with real-time filter search.
    - Model selection auto-saves immediately without requiring explicit "Save Preferences" click.
  - **OpenRouter Header Fix**:
    - Added mandatory `HTTP-Referer` and `X-Title` headers to OpenAI SDK client instances when connecting to OpenRouter, resolving the HTTP 401 "User not found" API error.

- **2026-07-28**:
  - **RAG-Lite Evidence Retrieval & Line-Level Symbol Tracking**:
    - Extracted exact line numbers for AST symbols in Python (`node.lineno`) and regex-parsed symbols in JS/TS/Rust/Go/C#/Java (`content[:m.start()].count('\n') + 1`) in `analyzer.py`.
    - Added `code_symbols` column to `session_records` database schema and SQLite FTS5 `session_records_fts` virtual table.
    - Updated `DatabaseManager.search_fts()` to match query terms against raw AST symbol lines and return structured raw code symbol matches.
    - Formatted `ChatWorker` system prompt to display Raw Source AST Symbols with exact file paths and line numbers so LLM answers cite source line numbers directly.
  - **Worker Thread Safety & Generation ID System (`chat_view.py`)**:
    - Implemented worker `gen_id` tracking system.
    - Added signal disconnection and thread termination (`.terminate()`) if cancellation times out (`wait(1000)`), preventing orphaned worker threads from emitting tokens into active chat views.
  - **Chat Stream & History Reliability**:
    - Replaced `QPlainTextEdit` string splitting with a dedicated `_current_response_buffer` token accumulator.
    - Rendered chat stream turns with styled HTML headers (`You:` in blue, `Assistant:` in emerald green) for scannable conversation turns.
    - Added single-click "Retry Request" button on failed chat requests.
  - **Polyglot Dependency Intelligence**:
    - Extended `analyzer.py` manifest parsing to extract per-dependency name and version details for `package.json` (`dependencies` & `devDependencies`), `Cargo.toml`, and `go.mod`.
  - **Token Estimate Guardrails**:
    - Added warning styling for high token count inputs (> 4,000 tokens) and pre-send context guardrail warnings (> 8,000 tokens) in `chat_view.py`.
  - **UI/UX Polish & Granular Diagnostics**:
    - Added 400ms minimum display timer for `thinking_bar` so fast local FTS searches don't flicker.
    - Formatted granular stage progress text (`Analyzing: X / Y files (Z%) — scanning dependencies`) and set `QSplitter` stretch factors (1:2 ratio) in `analyze_view.py`.
    - Added `⏳ Testing connection...` interim status badge on click in `settings_view.py`.
    - Replaced silent `except Exception: pass` swallow blocks in `analyzer.py` with `logging.warning()` trace outputs.
    - Added informative empty state cards and guidance across `kb_view.py` and `chat_view.py`.
  - **Automated Verification**:
    - 11/11 unit & service tests passing in `pytest` (`test_backend.py`).
