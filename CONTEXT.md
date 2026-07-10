# Git Reverse — Master Context Document

**Project**: Git Reverse — Git Repository Reverse Engineering Platform
**Version**: 1.0.0
**Date**: 2026-07-10
**Author**: Chethan Kumar
**Brand**: NEXUS LABS

## Product Vision
A local-first desktop/CLI platform that reverse-engineers any GitHub repository through deterministic analysis (AST parsing, dependency graphs, architecture extraction) and uses LLMs only for reasoning over already-extracted structured knowledge. Outputs professional-grade reconstruction prompts, learning roadmaps, architecture blueprints, and improvement suggestions.

## Core Principles (Constitution — Immutable)
1. **Local-First**: All data stays on user's machine. Cloud only for OpenRouter API and GitHub API.
2. **Analysis Before Reasoning**: Deterministic extraction → LLM reasoning. Never raw code to LLM.
3. **Evidence-Backed**: Every claim cites file path + line number. No hallucination.
4. **Plugin Architecture**: Every capability is a replaceable module.
5. **Keyboard-First UX**: No modal interruptions. Persistent status bar. Streaming markdown.
6. **Human-Readable Output**: Publishable quality. Obsidian/Linear aesthetic.
7. **Test-Driven**: >90% coverage. Integration tests for full pipeline.

## Technical Stack (Locked Decisions)
| Component | Choice | Rationale |
|-----------|--------|-----------|
| Language | Python 3.11+ | Ecosystem, tree-sitter bindings, SQLModel |
| TUI Framework | Textual + Rich | Premium terminal UI, streaming markdown |
| AST Parsing | tree-sitter official bindings | Stable, low overhead, selective loading |
| Database | SQLite WAL + SQLModel | Connection pooling, concurrent reads, local-first |
| Git Operations | pygit2 | Native C-speed, low memory vs GitPython |
| Incremental Analysis | Git commit hashes | O(1) comparison, immune to clock skew |
| Knowledge Graph | Adjacency list + recursive CTEs | No graph DB overhead, fast traversals |
| AI Provider | OpenRouter API | Multi-model support, user provides API key |
| Packaging | PyInstaller/Nuitka | Standalone binaries |

## Deployment Model
**Single-machine, local-first desktop/CLI tool.**
- Single user, no multi-tenancy
- Local storage: `~/.gitreverse/` (SQLite, cache, config)
- Local compute: all analysis on user's machine
- No distributed systems, no Redis, no message queues
- Concurrency: up to 5 simultaneous analysis tasks (configurable)

## Performance Targets
- Clone + analyze 10k LOC repo: <60s
- Knowledge graph query: <100ms
- Memory: <500MB for <100k LOC repos
- Disk: <1GB per analyzed repository

## Project Structure
```
gitreverse/
├── cli/           # Textual TUI application
├── core/          # Pipeline orchestrator
├── analyzers/     # Language, framework, dependency, architecture analyzers
├── parsers/       # tree-sitter parsers (pluggable per language)
├── models/        # Data models (Repository, File, Symbol, Dependency, etc.)
├── storage/       # SQLite database manager + migrations
├── git/           # pygit2 operations (clone, diff, auth)
├── llm/           # OpenRouter client + prompt templates
└── utils/         # Progress, logging, config
```

## Development Workflow
**Agentic Dev Stack**: spec → plan → tasks → implement. No manual coding.
Each phase produces artifacts that feed the next:
- `sp.constitution` → ratified principles
- `sp.specify` → feature specification (WHAT and WHY)
- `sp.plan` → technical implementation (HOW)
- `sp.tasks` → dependency-ordered task list
- Coding agent → implementation per task

## Current Status
- ✅ Phase 0 (Research): Complete. All technical decisions locked.
- ⏳ Phase 1 (Design): Pending. Need data model, contracts, quickstart.
- ⏳ Phase 2 (Tasks): Pending. Need task breakdown.
- ⏳ Phase 3 (Implement): Pending. Hand off to coding agent.

## Feature Roadmap
**V1 (CLI)**: Repository analysis pipeline, TUI, session management, prompt generation, multi-model support, skills/plugins.
**V2 (Desktop)**: Rust+Tauri desktop app, local vector DB, knowledge management, MCP integration.

## Non-Goals (Explicitly Out of Scope for V1)
- Distributed deployment
- Multi-tenancy / team collaboration
- Cloud-hosted service
- Code execution from analyzed repos (without explicit consent)
- Support for repositories >1M LOC (requires chunking, deferred)
