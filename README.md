# Git Reverse

> **Repository Intelligence Platform** — Transform any Git repository into structured knowledge.

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org)
[![uv](https://img.shields.io/badge/package_manager-uv-green.svg)](https://github.com/astral-sh/uv)
[![License: MIT](https://img.shields.io/badge/license-MIT-yellow.svg)](LICENSE)

Git Reverse is a local-first terminal platform that clones any Git repository, parses it into an AST-based knowledge graph, and lets you query, explore, and generate documentation from it using an LLM.

```
Repository → Clone → AST → Knowledge Graph → LLM → Answer
```

The LLM is always the **last** step — never the first.

---

## Quickstart

### Prerequisites
- Python 3.12+
- [uv](https://github.com/astral-sh/uv) (`pip install uv`)
- Git

### Install & Run

```bash
# Clone the project
git clone https://github.com/Chethankumar443/Git-Reverse-CLI.git
cd Git-Reverse-CLI

# Install all dependencies
uv sync

# Launch the interactive TUI
uv run git-reverse
```

---

## Commands

| Command | Description |
|---|---|
| `uv run git-reverse` | Launch the interactive TUI (default) |
| `uv run git-reverse analyze <url>` | Analyze a repo in headless/CI mode |
| `uv run git-reverse doctor` | Environment health check |
| `uv run git-reverse config --show` | View current configuration |
| `uv run git-reverse config --set-key <KEY>` | Store OpenRouter API key in OS keychain |
| `uv run git-reverse --help` | Show all commands |

### Example — Headless analysis

```bash
uv run git-reverse analyze https://github.com/tiangolo/fastapi
uv run git-reverse analyze ./my-local-project --mode architecture
```

---

## Configuration

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

Or store secrets securely in the OS keychain (recommended):

```bash
uv run git-reverse config --set-key YOUR_OPENROUTER_API_KEY
```

---

## Architecture

```
src/git_reverse/
├── config/        # Pydantic settings + OS keychain integration
├── core/          # Event bus, exceptions, structured logging
├── ingestion/     # Git cloner (async + retry) + file validator
├── storage/       # SQLite DAOs, auto-migrations, knowledge graph schema
└── tui/           # Textual TUI application
```

See the [`docs/`](docs/) directory for the full engineering specification suite.

---

## Development

```bash
# Run tests
uv run pytest tests/ -v

# Type check
uv run mypy src/

# Lint
uv run ruff check src/
```

---

## License

MIT
