# Git Reverse Intelligence System (GRIS)

[![PyPI version](https://img.shields.io/pypi/v/gitreverse.svg?color=blue)](https://pypi.org/project/gitreverse/)
[![Python Version](https://img.shields.io/badge/python-3.11%20%7C%203.12-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![CI Pipeline](https://github.com/Chethankumar443/Git-Reverse-Intelligence-System--GRIS-/actions/workflows/ci.yml/badge.svg)](https://github.com/Chethankumar443/Git-Reverse-Intelligence-System--GRIS-/actions)

> **Git Reverse (GRIS)** is a production-grade repository intelligence platform that performs deep AST/manifest parsing, entrypoint ranking, line metric extraction, FTS5-enabled hybrid RAG chat, secret scanning, and architecture prompt generation for public and private GitHub repositories.

---

## ⚡ Quick Install

### Via `pip` / `pipx`
```bash
pip install gitreverse
```

### Windows Desktop Installer (.exe)
Download the standalone **Windows Installer** (`GitReverse-Setup-1.1.0.exe`) directly from the [Releases](https://github.com/Chethankumar443/Git-Reverse-Intelligence-System--GRIS-/releases) page. The installer automatically registers **Git Reverse** in your Start Menu and creates a Desktop Shortcut.

---

## 🚀 Getting Started

1. **Launch the Desktop Application**:
   ```bash
   gitreverse
   ```
2. **First-Run Wizard**: Set up your free or preferred LLM Provider (OpenRouter, Groq, OpenAI, DeepSeek, or Ollama Local). Your API keys are stored safely in Windows Credential Manager.
3. **Analyze Repositories**: Enter any public GitHub repository URL to generate deep architecture specs and prompt blueprints.

---

## 🔑 Features Overview

| Feature | Description |
|---|---|
| **AST Ingestion Engine** | Parses imports, classes, functions, and entry points with structural ranking. |
| **Hybrid FTS5 RAG** | Lightning-fast full-text search across codebase files and commit histories. |
| **BYOK Model Selector** | Connect to OpenRouter, Groq, OpenAI, DeepSeek, or Ollama Local with dynamic model list fetching. |
| **Spending Protection** | Set daily and monthly spend limits with automatic warning or execution blocking. |
| **Knowledge Base** | Re-open past analyzed sessions, export JSON backups, and inspect complete audit trails. |
| **OS Credential Manager** | API keys and GitHub PATs remain encrypted in local OS keyring. |

---

## ⌨️ Command Line Interface (CLI)

```bash
# Display version
gitreverse --version

# Display CLI help options
gitreverse --help

# Reset setup wizard state
gitreverse --reset-setup
```

---

## ⚙️ Configuration & Security

Configuration settings are stored locally in `%LOCALAPPDATA%\GitReverse\config.json` (`~/.gitreverse/config.json`).
All sensitive API keys and personal access tokens are stored securely in your OS credential store using `keyring`.

---

## 🛡️ License

This project is licensed under the [MIT License](LICENSE).
Created by **Chethan Kumar / NEXUS LABS**.
