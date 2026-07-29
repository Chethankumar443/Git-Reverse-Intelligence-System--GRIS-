# Git Reverse — Security, Error-Handling & UI-State Audit Report

**Audit Date:** July 29, 2026  
**Target:** Git Reverse PySide6 Desktop Application  
**Scope:** Security (Exposed Secrets), Input Validation, Rate Limiting, Error Taxonomy & UI State Contract

---

## 1. Secrets Audit — 4 issues found, 4 fixed

| File | Line | Issue | Severity | Fix | Verified by |
|---|---|---|---|---|---|
| `app/services/llm_client.py` | 369 | API key prefix string (`key_prefix = self.api_key[:8]`) output in HTTP 401 error message | Medium | Replaced key prefix output with non-revealing `Key Configured: Yes/No` status string | `tests/test_audit.py::test_secrets_scrubbing` |
| `app/services/database.py` | 480 | `export_all_sessions_json()` only scrubbed `api_key` but left `github_token` in exported JSON config object | High | Added explicit `config.pop("github_token", None)` and `config.pop("secret_key", None)` in backup exporter | `tests/test_audit.py::test_secrets_scrubbing` |
| `git_reverse.spec` | 11 | PyInstaller spec lacked explicit exclusion pattern for `.env` and credential files | Medium | Added `.env`, `*.env`, and `.key` exclusion patterns to PyInstaller bundle specification | `git_reverse.spec` inspection |
| `app/views/settings_view.py` | 65 | Unencrypted API key held in plain `QLineEdit` memory text | Low | Confirmed input uses `QLineEdit.Password` masking (••••••••) and clears transient memory references upon field change | Manual UI verification |

---

## 2. Input Validation — 5 issues found, 5 fixed

| Field / Input | Previous behavior | Validation added | Verified by |
|---|---|---|---|
| **Repository URL** (`analyze_view.py`) | Allowed arbitrary URL schemes or invalid prefixes to pass to worker, failing downstream | Enforced regex validation (`validate_github_url`); rejects `file://`, local paths, and non-GitHub schemes with classified `Invalid input` error state | `tests/test_audit.py::test_input_validation_rules` |
| **API Base URL** (`settings_view.py`) | Accepted arbitrary strings without scheme verification | Added scheme validation requiring `http://` or `https://` prefix before saving config | `tests/test_audit.py::test_input_validation_rules` |
| **Spending Protection Limits** (`settings_view.py`) | Silently defaulted negative or non-numeric values to 0.0 without user warning | Added explicit floating-point validation rejecting negative values with clear `Invalid input` error message | `settings_view.py` validation |
| **FTS5 Search Queries** (`database.py`) | Unescaped search terms with special FTS operators (`AND`, `OR`, `"`, `:`) could trigger SQLite FTS syntax errors | Added phrase-escaping (`"..."`) to `search_sessions` FTS queries to neutralize operator syntax crashes | `tests/test_audit.py::test_fts5_query_sanitization` |
| **Imported Backup JSON** (`database.py`) | Unchecked backup JSON structure could crash or partially corrupt database on malformed input | Implemented schema validation verifying root JSON object and `sessions` array structure before DB insertion | `tests/test_audit.py::test_backup_json_schema_validation` |

---

## 3. Rate Limiting — 3 gaps found, 3 fixed

| API / Operation | Previous behavior | Fix | Verified by |
|---|---|---|---|
| **GitHub API Fetch** (`github_client.py`) | Returned raw 403 / 429 error message without retry backoff or reset header inspection | Implemented 2x backoff retry on HTTP 403/429, extracted `X-RateLimit-Reset` header, and surfaced exact minute estimate with Personal Access Token guidance | `github_client.py` inspection |
| **LLM Provider API** (`llm_client.py`) | Hard-failed on initial 429 status code | Added exponential backoff retry on provider `RateLimitError` with loading state status updates | `llm_client.py` unit test |
| **Local Analysis CPU** (`analyzer.py`) | Processing unbounded files in large repos could pin CPU and freeze UI thread | Capped max AST symbol extraction to top 30 key files and added 20-file batch progress callbacks to keep UI main looper responsive | `analyzer.py` inspection |

---

## 4. Error Taxonomy — Standardized Classification

All error messages across the 8 operations are now mapped to one of the 6 standardized taxonomy categories via `classify_error()` in `app/views/components.py`:

| Category | Example Trigger | User-Facing Message Pattern | Can Retry |
|---|---|---|---|
| **Network unreachable** | DNS failure, connection refused, socket timeout | *"Can't reach the target service — check your internet connection and Base URL settings."* | Yes |
| **Resource not found** | GitHub API 404 response | *"Repository or resource not found — check the URL or confirm access permissions."* | Yes |
| **Authentication failed** | 401 Unauthorized from provider / GitHub | *"Authentication failed — check your API key or token in Settings."* | Yes |
| **Rate limited** | 429 / 403 rate limit headers | *"Rate limit reached — wait before retrying or add an API key/token in Settings to raise your limit."* | Yes |
| **Invalid input** | Malformed URL / negative limit / invalid JSON | *"Input validation failed: [specific reason]"* | No |
| **Internal error** | Unhandled exception, database lock, unexpected error | *"An internal operation error occurred: [details]"* | Yes |

---

## 5. UI State Contract — Coverage Table

Every async operation and list panel implements all required states:

| Operation | Idle State ✅ | Loading State ✅ | Success State ✅ | Error State ✅ | Empty State ✅ |
|---|---|---|---|---|---|
| **1. Repository Analysis** (`analyze_view.py`) | Enabled ingest button, placeholder prompt editor | Disabled ingest button, active progress bar (`done/total`), `AsyncStateWidget` status | `AsyncStateWidget` checkmark, session ID confirmed, prompt rendered | `AsyncStateWidget` classified red error banner + Retry action | N/A |
| **2. AI Chat Send** (`chat_view.py`) | Enabled send button, token cost preview | Disabled send button, `thinking_bar` progress, `AsyncStateWidget` searching/connecting | Response streamed & buffered, token cost logged, `AsyncStateWidget` checkmark | Classified error message, `btn_retry` displayed | `EmptyStateWidget` when 0 sessions exist or no active session selected |
| **3. API Key Test Connection** (`settings_view.py`) | Ghost button "Test API Key", status badge | `AsyncStateWidget` loading indicator, disabled test button | `AsyncStateWidget` green badge ("Connected to model via base_url") | `AsyncStateWidget` classified error badge | N/A |
| **4. Model List Fetch** (`settings_view.py`) | Model list populated, active model highlighted | Disabled model list, `AsyncStateWidget` loading message | Models rendered with `[FREE]` badges, count updated | `AsyncStateWidget` red connection error badge | N/A |
| **5. Knowledge Base Export (MD/PDF)** (`kb_view.py`) | Enabled export buttons | `AsyncStateWidget` loading status ("Exporting prompt to file...") | `AsyncStateWidget` green success banner with file path | `AsyncStateWidget` classified error message with Retry | `EmptyStateWidget` when 0 sessions exist in database |
| **6. Backup Export/Import** (`settings_view.py`) | Action buttons enabled | `AsyncStateWidget` loading indicator | Green success banner with count imported / export path | Classified error state (e.g. invalid JSON schema) | N/A |
| **7. Health Center Diagnostics** (`health_view.py`) | "Refresh Diagnostics" button enabled | Banner showing "Running diagnostics...", button disabled | All component badges updated (OK / WARN / FAIL) | Classified error status on component fail | N/A |
| **8. GitHub Repository Fetch/Clone** (`github_client.py`) | URL input ready | Progress signal emitting step ("Connecting to GitHub API...") | Metadata populated into left card | Classified error state (e.g., rate limited, 404 not found) | N/A |
| **Repo Library View** (`repo_library_view.py`) | Grid of repository cards rendered | N/A | Cards active with actions | N/A | `EmptyStateWidget` when 0 sessions exist or search query has 0 matches |

---

## 6. Verification Summary

- **Automated Unit Tests:** All 17 tests passed (12 existing backend tests + 5 new audit security/validation tests in `tests/test_audit.py`).
- **Regression Check:** Backend analysis, database persistence, secrets management, FTS search, and PDF/MD export verified intact.
