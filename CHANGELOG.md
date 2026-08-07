# Changelog

All notable changes to the **Git Reverse Intelligence System (GRIS)** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.1.0] - 2026-08-07

### Added
- **Windows Installer & Setup**: Introduced Inno Setup release workflow generating single executable installer (`GitReverse-Setup-1.1.0.exe`).
- **Desktop Shortcut Support**: Automated creation and registration of Windows Desktop (`Git Reverse.lnk`) and Start Menu shortcuts.
- **Checksum Integrity Verification**: Automatic SHA-256 hash calculation for release artifacts (`SHA256SUMS.txt`).
- **GitHub Actions Release Workflow**: Added `.github/workflows/release.yml` automated draft release workflow triggered on version tags.

### Changed
- **UI/UX & Typography Overhaul**: Standardized enterprise typography font stack (`-apple-system`, `Segoe UI`, `Inter`) across all workspace views.
- **Theme Palette Calibration**: Calibrated light and dark mode design tokens in `styles.py` for high-contrast legibility and refined card borders.
- **PAT Setup Guide Card**: Redesigned GitHub Personal Access Token setup card in Settings view with theme-aware `g-info-card` callouts.
- **Single Source Versioning**: Consolidated application version metadata across GUI, spec files, and installer configuration into `app/_version.py`.

### Fixed
- **Health Center Status Badges**: Resolved doubled status badge text bug ("OK OK" -> "OK") in `health_view.py`.
- **Live Theme Repolish**: Enhanced recursive widget unpolish/re-polish pass for instant theme switching without requiring application restart.
- **Monospace Text Gaps**: Fixed Qt RichText code block spacing bugs on setup instructions.

---

## [1.0.0] - 2026-08-01

### Added
- Initial public desktop application release of **Git Reverse**.
- Repository ingestion engine supporting SQLite/FTS5 hybrid search indexing.
- Native PySide6 Qt6 desktop interface with BYOK (Bring Your Own Key) model picker.
- Multi-provider LLM support (OpenRouter, Groq, OpenAI, DeepSeek, Ollama Local).
