---
document: trd.md — Technical Requirements (distilled, frozen)
supersedes: the original trd.md (round-3 draft) — DELETE the old file
companion_to: DESIGN.md (implementation), CHARTER.md (impact/ethics), prd.md (product reqs)
rule: this file states technical REQUIREMENTS only. No code. Implementation → DESIGN.md §N.
---

# Git Reverse — Technical Requirements Document

## 1. Architecture pattern & invariants
- Pattern: MVVM. UI holds no business logic.
- INV1 UI layer never imports `requests`/`httpx`/`sqlite3` directly.
- INV2 No blocking operation on the main thread; all I/O on worker threads.
- INV3 Secrets never written to disk; OS keyring only. Non-secret config in plain JSON.
- Impl: DESIGN §2.1, §2.2.

## 2. System components
| Component | Responsibility | Ref |
|---|---|---|
| View (PySide6) | Sidebar + top bar + stacked content (empty/conversation) + dock + settings | DESIGN §5 |
| ViewModels | Analysis / Session / Settings state | DESIGN §2.1 |
| GitHub client | URL validation, metadata, tree, file download, cleanup | DESIGN §6.1 |
| LLM client | BYOK streaming over OpenAI-compatible `base_url` | DESIGN §6.2 |
| Analyzer | Language detection, dependency extraction, AST summaries | DESIGN §6.3 |
| Database | SQLite + ORM, session persistence | DESIGN §6.4 |
| Secrets | OS keyring wrapper | DESIGN §6.5 |
| Exporters | PDF (weasyprint) + Markdown | DESIGN §6.6, §6.7 |
| Workers | Background analysis + export threads | DESIGN §7 |

## 3. Data flow (repository analysis)
1 Validate URL → 2 fetch metadata+tree → 3 filter ignored dirs → 4 download to secure
temp dir (size-capped) → 5 analyze structure/deps/language + detect LICENSE → 6 stream
summary to LLM → 7 stream tokens to UI → 8 persist session + delete temp dir.
Security annotations per step: DESIGN §3.

## 4. Data model (session record)
| Field | Type | Notes |
|---|---|---|
| id | int PK | auto |
| repo_url | str | validated |
| repo_name | str | owner/repo |
| language | str | primary |
| file_count | int | |
| generated_prompt | text | streamed result |
| model_used | str | BYOK model id |
| source_license | str | detected license id or "none" (req US9/FR8) |
| created_at | datetime | |
| status | str | pending/analyzing/complete/error |
Storage: SQLite in user dir, WAL mode, ORM-only access. Schema/impl: DESIGN §6.4.

## 5. External interfaces
- GitHub REST API v3 (token from keyring; scoped `repo`+`read:user`).
- OpenAI-compatible chat completions (streaming) via configurable `base_url`; presets for
  OpenAI/OpenRouter/Groq/DeepSeek/xAI/local-Ollama/custom. No shipped keys.
- OS credential manager (`keyring`) for secrets; plain JSON for provider/model/theme.
- Local filesystem: temp dir (auto-deleted), export dir (user-chosen), SQLite db.
- Impl: DESIGN §6.1, §6.2, §6.5.

## 6. Non-functional requirements
| NFR | Requirement | Ref |
|---|---|---|
| Perf | UI thread never blocks; streaming render | DESIGN §2.2, §7 |
| Security | No `shell=True`; ORM-only SQL; `autoescape` templates; URL regex; size cap | DESIGN §9 |
| Resilience | Exp backoff; honor 429 `Retry-After`; WAL + busy_timeout | DESIGN §8, §6.4 |
| Privacy | No PII to LLM beyond repo code; temp auto-deleted; logs redacted | DESIGN §3, §9 |
| Local ownership | Data in user dir; export-all + delete-all available | DESIGN §6.4 |
| Accessibility | 44px primary targets; Enter submits; visible focus ring (contrast audit deferred to beta) | DESIGN §4.5, §5.4 |
| Distribution | Single signed `.exe`, no Python prerequisite | DESIGN §12 P4 |
| Telemetry | None by default; any future telemetry opt-in + documented | CHARTER §3 |

## 7. Error handling strategy
| Condition | Behavior | Ref |
|---|---|---|
| Timeout | Exp backoff, 3 retries; UI toast | DESIGN §8 |
| 429 rate limit | Parse `Retry-After`; disable Analyze + countdown | DESIGN §8 |
| 404 repo | Surface "not found" | DESIGN §8 |
| 401 key | Surface "invalid key" → Settings | DESIGN §8 |
| DB lock | WAL + busy_timeout (transparent) | DESIGN §6.4 |
| Stream interrupted | Save partial; badge "interrupted" | DESIGN §8 |
| Malicious repo file | Read-only parse in try/except; **never execute** analyzed code | CHARTER §3.1 |

## 8. Dependencies
PySide6 ≥6.6 · openai ≥1.30 (BYOK adapter) · weasyprint ≥60 · Jinja2 ≥3.1 ·
requests ≥2.31 · SQLAlchemy ≥2.0 · keyring ≥24. Pin exact versions before packaging.
Impl: DESIGN §14.

## 9. Build & distribution
PyInstaller → NSIS single `.exe`; bundle Geist fonts + PDF templates; no console window.
Impl: DESIGN §12 P4, §13.

## 10. Traceability (requirement → implementation)
| Requirement | Where implemented |
|---|---|
| FR1–FR3, US2–US3, US8 | DESIGN §3, §6.1–§6.3, §7 |
| FR4–FR6, US5 | DESIGN §5.1, §6.4 |
| FR7, US6 | DESIGN §5.2, §6.5 |
| FR8, US9 (responsible use) | CHARTER §2.2; DESIGN §6.2 (system prompt), §6.6/§6.7 (footer) |
| FR9, US7 | DESIGN §4.1 |
| All NFRs | DESIGN §8, §9; CHARTER §3 |
| Impact/SDG claims | CHARTER §1 (interpretive; SDG-4 conditional on FR8) |

> Freeze. This prd.md + trd.md replace the round-3 drafts; DESIGN.md + CHARTER.md
> remain. Four docs, four jobs, zero duplicated code. No further spec documents.
