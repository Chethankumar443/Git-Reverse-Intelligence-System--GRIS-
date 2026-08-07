<div align="center">

```
 ██████╗ ██╗████████╗      ██████╗ ███████╗██╗   ██╗███████╗██████╗ ███████╗███████╗
██╔════╝ ██║╚══██╔══╝      ██╔══██╗██╔════╝██║   ██║██╔════╝██╔══██╗██╔════╝██╔════╝
██║  ███╗██║   ██║         ██████╔╝█████╗  ██║   ██║█████╗  ██████╔╝███████╗█████╗
██║   ██║██║   ██║         ██╔══██╗██╔══╝  ╚██╗ ██╔╝██╔══╝  ██╔══██╗╚════██║██╔══╝
╚██████╔╝██║   ██║         ██║  ██║███████╗ ╚████╔╝ ███████╗██║  ██║███████║███████╗
 ╚═════╝ ╚═╝   ╚═╝         ╚═╝  ╚═╝╚══════╝  ╚═══╝  ╚══════╝╚═╝  ╚═╝╚══════╝╚══════╝
```

**Reverse-engineer any GitHub repository with AI.**  
Local-first · Evidence-backed · Streaming terminal UI

[![PyPI version](https://img.shields.io/pypi/v/gitreverse?color=58a6ff&labelColor=0d1117)](https://pypi.org/project/gitreverse/)
[![Python ≥ 3.11](https://img.shields.io/badge/python-%E2%89%A53.11-58a6ff?labelColor=0d1117)](https://www.python.org/downloads/)
[![CI](https://img.shields.io/github/actions/workflow/status/Chethankumar443/Git-Reverse-Intelligence-System--GRIS-/ci.yml?branch=main&label=CI&labelColor=0d1117)](https://github.com/Chethankumar443/Git-Reverse-Intelligence-System--GRIS-/actions)
[![Licence: MIT](https://img.shields.io/badge/licence-MIT-2ea043?labelColor=0d1117)](LICENSE)

</div>

---

## What is Git Reverse?

Git Reverse clones any GitHub repository locally, parses it with static analysis (AST, dependency graphs, framework detection), stores the knowledge in a local SQLite database, and uses an AI model of your choice to answer questions about it — in a premium terminal UI.

**Everything stays on your machine.** Only the OpenRouter API call leaves your computer.

```
$ gitreverse

 ██████╗ ██╗████████╗     REVERSE  ...
 
> https://github.com/facebook/react

[CLONE] Cloning repository... ████████░░░░  60%
[PARSE] Running AST analysis... ████████████ 100%

✓ Analysis complete: react

> What design patterns does this use?

● The React codebase uses the Composite pattern extensively through...
```

---

## Quick Install

### pip (recommended)

```bash
pip install gitreverse
gitreverse
```

### pipx (isolated environment)

```bash
pipx install gitreverse
gitreverse
```

### From source

```bash
git clone https://github.com/Chethankumar443/Git-Reverse-Intelligence-System--GRIS-.git
cd Git-Reverse-Intelligence-System--GRIS-
pip install -e .
gitreverse
```

### Standalone binary (no Python needed)

Download the pre-built binary for your platform from the [Releases page](https://github.com/Chethankumar443/Git-Reverse-Intelligence-System--GRIS-/releases/latest).

| Platform | File |
|----------|------|
| Linux (x86_64) | `gitreverse-linux-x86_64` |
| macOS (x86_64 + arm64) | `gitreverse-macos` |
| Windows (x64) | `gitreverse-windows.exe` |

---

## Setup (3 steps)

The first time you run `gitreverse`, a wizard walks you through setup:

1. **Username** — personalises your session history
2. **OpenRouter API key** — get a free key at [openrouter.ai/keys](https://openrouter.ai/keys) (no credit card required)
3. **AI model** — choose from the list of free models fetched automatically

Configuration is saved at `~/.gitreverse/config.toml`. Your API key is encrypted at rest.

---

## Features

| Feature | Description |
|---------|-------------|
| 🔬 **AST Analysis** | Tree-sitter parsing for Python, JS/TS, Rust, Go, Java, C/C++ |
| 🏗️ **Architecture Detection** | Frameworks, design patterns, folder structure |
| 📦 **Dependency Mapping** | pip, npm, cargo, go.mod, maven |
| 🤖 **AI Q&A** | Ask anything about the repo — powered by your chosen LLM |
| 💾 **Session Persistence** | Save and resume past analysis sessions |
| 📤 **Export** | Markdown, JSON, plain text reports |
| 📋 **Recreation Prompt** | Auto-generate a prompt to rebuild the project from scratch |
| 🔒 **Local-First** | All data stored in `~/.gitreverse/` — nothing uploaded |

---

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `/` | Open command palette |
| `Enter` | Send input / execute command |
| `Ctrl+K` | Focus input bar |
| `Ctrl+L` | Clear chat history |
| `Ctrl+Q` | Quit and save session |
| `Escape` | Cancel active analysis |
| `↑ ↓` | Navigate model selector |

---

## Commands

### AI Analysis
| Command | Description |
|---------|-------------|
| `/explain` | AI explains the repository purpose and structure |
| `/architecture` | AI explains architecture patterns and design |
| `/folders` | AI explains folder structure and organisation |
| `/suggest` | AI suggests improvements and best practices |
| `/deep-dive` | Comprehensive deep-dive analysis |

### Repository Info
| Command | Description |
|---------|-------------|
| `/tree` | Show repository folder structure |
| `/readme` | Show README summary |
| `/deps` | List all dependencies by type |
| `/frameworks` | Show detected frameworks with evidence |
| `/languages` | Show language breakdown with file counts |

### Session Management
| Command | Description |
|---------|-------------|
| `/sessions` | List all saved sessions |
| `/resume ID` | Resume a saved session by ID |
| `/save` | Save current session manually |
| `/compact` | Summarise current session content |

### Export & Generation
| Command | Description |
|---------|-------------|
| `/export md` | Export analysis to Markdown file |
| `/export json` | Export analysis to JSON file |
| `/export txt` | Export analysis to plain text file |
| `/prompt` | Generate a recreation prompt for this project |
| `/blueprint` | Generate a development blueprint |

### Configuration
| Command | Description |
|---------|-------------|
| `/settings` | View current settings and available models |
| `/config api-key KEY` | Set OpenRouter API key |
| `/config model MODEL_ID` | Change AI model |
| `/config username NAME` | Change username |

---

## Configuration

Config file: `~/.gitreverse/config.toml`

```toml
[user]
username = "Chethan"
is_setup_complete = true

[llm]
api_key_encrypted = "..."   # Fernet-encrypted
model = "google/gemma-3-27b-it:free"
temperature = 0.7
base_url = "https://openrouter.ai/api/v1"

[analysis]
max_concurrent_tasks = 5
memory_limit_mb = 500

[database]
db_path = "~/.gitreverse/cache.db"
```

### CLI flags

```
gitreverse --version         Print version and exit
gitreverse --reset-setup     Clear credentials and re-run the setup wizard
```

---

## Performance Targets

| Metric | Target |
|--------|--------|
| Clone + analyse 10k LOC repo | < 60 s |
| Knowledge graph query | < 100 ms |
| Memory (< 100k LOC repo) | < 500 MB |
| Disk per analysed repo | < 1 GB |

---

## Architecture

```
gitreverse/
├── cli/           Textual TUI application + setup wizard
├── core/          Async analysis pipeline orchestrator
├── analyzers/     Language, framework, dependency, architecture analysers
├── parsers/       tree-sitter parsers (pluggable per language)
├── models/        SQLModel data models (Repository, File, Symbol, …)
├── storage/       SQLite database manager + WAL migrations
├── git/           pygit2 clone + diff operations
├── llm/           OpenRouter client + prompt templates + context builder
└── utils/         Config, crypto (API key encryption), logging
```

All analysis is deterministic. The LLM only reasons over the pre-extracted structured knowledge — raw source code never leaves your machine.

---

## Contributing

1. Fork the repo and create a branch: `git checkout -b feat/my-feature`
2. Make your changes with tests: `pytest tests/ -x`
3. Lint: `ruff check gitreverse/`
4. Open a pull request

See [CHANGELOG.md](CHANGELOG.md) for the project history.

---

## Licence

[MIT](LICENSE) © 2026 Chethan Kumar / NEXUS LABS
