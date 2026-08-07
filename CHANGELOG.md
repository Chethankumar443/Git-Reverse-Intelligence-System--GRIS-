# Changelog

All notable changes to **Git Reverse** are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0] — 2026-08-07

### Added

#### Core Analysis Pipeline
- Full async analysis pipeline: clone → scan → AST parse → framework detect → dependency extract → symbol index
- `pygit2`-backed Git operations with incremental analysis via commit-hash comparison
- `tree-sitter` AST parsing with per-language grammar loading (Python, JavaScript, TypeScript, Rust, Go, Java, C/C++)
- Framework detection with evidence references (file path + version)
- Dependency extraction for `pip`, `npm`, `cargo`, `go.mod`, `maven`
- Folder tree builder with configurable depth

#### TUI Application (`gitreverse`)
- Full Textual-based terminal UI with GitHub Dark colour scheme (`#0d1117` palette)
- 4-step first-run setup wizard (username → API key → model selection → confirmation)
- Live streaming markdown output from LLM responses
- Progress strip with multi-stage pipeline progress bar
- Mode badge switching between `ANALYZE` and `QUERY` modes
- Command palette with `/` prefix autocomplete popup
- Session persistence — save, list, resume past sessions

#### AI Integration (OpenRouter)
- Streaming LLM client via OpenRouter API (multi-model support)
- Free model auto-fetching and interactive model selector
- Analysis prompts: `/explain`, `/architecture`, `/folders`, `/suggest`, `/deep-dive`
- Context builder that injects structured knowledge graph data (not raw code) into prompts
- Session compaction with `/compact`

#### Export
- Export analysis to Markdown, JSON, and plain text via `/export [md|json|txt]`
- Recreation prompt generator (`/prompt`)
- Development blueprint generator (`/blueprint`)

#### Configuration & Security
- Config stored at `~/.gitreverse/config.toml`
- API key encrypted at rest using Fernet symmetric encryption
- `--reset-setup` flag to clear credentials and re-run wizard
- `--version` / `-V` flag

#### Developer
- `pyproject.toml` with full metadata, classifiers, and URLs
- MIT Licence
- GitHub Actions CI (lint + test matrix on ubuntu + windows, Python 3.11 + 3.12)
- GitHub Actions Release (PyInstaller binaries for Linux/Windows/macOS + PyPI publish)

### Fixed
- Duplicate CSS rules for `.setup-btn`, `.setup-btn-skip`, `#btn-row-*` in the TUI stylesheet
- Duplicate `#status-bar` CSS definition (only last definition was applied)
- Invalid Rich markup tag `[model-context]` in `ModelSelector.render()` — now uses explicit `[#8b949e]` hex colour
- Unresolved Textual theme variables (`$accent`, `$success`, `$text-muted`) in `AnalysisProgressPanel` — replaced with explicit hex values that work on any theme
- ASCII logo overflow on terminals narrower than 95 columns — compact fallback logo added
- Duplicate `load_config()` call in `main()` — `GitReverseApp.__init__` already handles config loading
- API key input field now uses `password=True` to mask the key during entry

### Changed
- Setup wizard auto-advance after API key validation now waits 1.5 s so the "✓ Validated" message is readable before proceeding
- Completion screen now shows checkmark summary table instead of plain text
- Setup steps now show "Step X of 4" progress indicator
- API key steps 2 and 3 now show "ESC to go back" hint
- Welcome screen status indicator uses `●` prefix for connected/disconnected state
- Logo automatically scales to terminal width (wide ≥ 95 cols, compact < 95 cols)

---

[1.0.0]: https://github.com/Chethankumar443/Git-Reverse-Intelligence-System--GRIS-/releases/tag/v1.0.0
