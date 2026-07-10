# Git Reverse Constitution

## Core Principles

### I. Local-First Architecture
All data, sessions, analysis results, prompts, and configurations MUST remain on the user's machine by default.
- SQLite for structured storage
- Local vector database for embeddings
- File-based cache for repository analysis
- Cloud services limited to: OpenRouter API, GitHub API (only when explicitly needed)
- No telemetry without explicit opt-in
- No mandatory account creation

### II. Analysis Before Reasoning
The LLM is a reasoning layer, NOT a data extraction layer.
- Repository MUST be cloned and analyzed deterministically first
- AST parsing (tree-sitter) extracts symbols, imports, call graphs
- Dependency analysis builds package graphs
- Architecture graphs are constructed before any LLM invocation
- LLM receives structured knowledge, not raw code
- Every LLM response must cite evidence from the analysis pipeline

### III. Evidence-Backed Responses
Never hallucinate repository structure.
- Every claim about a repository must trace to parsed artifacts
- "This project uses React" is forbidden
- "This project uses React because package.json declares react@18.2.0 as a dependency" is required
- Confidence levels must be explicit: [Certain], [Likely], [Guessing]

### IV. Plugin Architecture Over Hardcoding
Every capability is a replaceable module.
- Language parsers are plugins (tree-sitter grammars)
- Framework detectors are plugins
- Analysis strategies are plugins
- Output formatters are plugins
- No feature is hardcoded into the core pipeline

### V. Keyboard-First, Non-Blocking UX
The interface must never interrupt the user's flow.
- No modal dialogs for critical workflows
- Persistent status bar showing mode, model, repository, session state
- Streaming markdown with incremental rendering
- Global search (Ctrl+K) across all content
- Every workflow must be achievable without mouse

### VI. Human-Readable Output
Every output must be publishable quality.
- Markdown must render cleanly in Obsidian, Notion, VS Code
- Code blocks must be syntactically highlighted
- Architecture diagrams must be exportable (Mermaid, PlantUML)
- No "AI-generated" aesthetic—think Linear, Obsidian, VS Code docs

### VII. Test-Driven Development (NON-NEGOTIABLE)
- All core pipeline components have >90% test coverage
- Integration tests verify end-to-end analysis workflows
- Performance benchmarks for repository analysis (target: <30s for 10k LOC repos)
- Security tests for sandboxed execution

## Additional Constraints

### Technology Stack (V1)
- Language: Python 3.11+
- TUI Framework: Textual + Rich
- Input: Prompt Toolkit
- Storage: SQLite (via SQLModel or raw sqlite3)
- Analysis: tree-sitter, GitPython/pygit2, NetworkX
- AI: OpenRouter API (multi-model)
- Packaging: PyInstaller/Nuitka for standalone binaries

### Performance Targets
- Repository clone + analysis: <60s for repos <50k LOC
- LLM response latency: <3s for first token (streaming)
- Memory footprint: <500MB for typical sessions
- Disk usage: <1GB per analyzed repository (including cache)

### Security Requirements
- No code execution from analyzed repositories without explicit user consent
- Sandboxed subprocess for any dynamic analysis
- Secrets (API keys) stored in OS keychain or encrypted local config
- No network calls except to whitelisted endpoints (OpenRouter, GitHub)

## Governance

This constitution supersedes all implementation decisions. Any feature, architectural choice, or technical debt must be justified against these principles. Violations require:
1. Documentation in Complexity Tracking table
2. Explanation of why simpler alternative was rejected
3. Migration plan to eventual compliance

**Version**: 1.0.0 | **Ratified**: 2026-07-10 | **Last Amended**: 2026-07-10
