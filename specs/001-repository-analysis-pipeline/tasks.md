# Tasks: Repository Analysis Pipeline

**Date**: 2026-07-10
**Spec**: [spec.md](./spec.md)
**Plan**: [plan.md](./plan.md)
**Status**: Draft (Pending Review)

This task list defines the execution steps in dependency order for the Repository Analysis Pipeline. Each task contains clear acceptance criteria and is designed to be independently testable.

---

## Task List

### Phase 1: Foundation & Data Layer

#### TSK-001: Project Skeleton & Configuration Setup
- **Description**: Initialize the Python package structure and config management.
- **Dependencies**: None
- **Files**:
  - `[NEW] gitreverse/__init__.py`
  - `[NEW] gitreverse/utils/config.py`
  - `[NEW] gitreverse/utils/logging.py`
  - `[NEW] pyproject.toml`
- **Acceptance Criteria**:
  - `gitreverse/utils/config.py` loads `~/.gitreverse/config.toml` with default concurrent tasks = 5.
  - Command `python -m gitreverse.utils.config` validates and prints config.

#### TSK-002: SQLModel Entities Definition
- **Description**: Define database tables mapped as SQLModels.
- **Dependencies**: TSK-001
- **Files**:
  - `[NEW] gitreverse/models/__init__.py`
  - `[NEW] gitreverse/models/repository.py`
  - `[NEW] gitreverse/models/file.py`
  - `[NEW] gitreverse/models/symbol.py`
  - `[NEW] gitreverse/models/dependency.py`
  - `[NEW] gitreverse/models/framework.py`
  - `[NEW] gitreverse/models/architecture.py`
  - `[NEW] gitreverse/models/knowledge_graph.py`
- **Acceptance Criteria**:
  - DB schema matching `data-model.md` matches entities correctly.
  - Run SQLModel metadata creation without syntax errors.

#### TSK-003: SQLite WAL Storage Manager
- **Description**: Setup database engine, WAL configuration, and base migration mechanism.
- **Dependencies**: TSK-002
- **Files**:
  - `[NEW] gitreverse/storage/__init__.py`
  - `[NEW] gitreverse/storage/database.py`
  - `[NEW] gitreverse/storage/queries.py`
- **Acceptance Criteria**:
  - `DatabaseManager` runs initialization and sets SQLite to WAL mode.
  - Concurrent read-write test demonstrates successful SQLite access without locking database errors.

---

### Phase 2: Core Subsystems (Git & AST Parsing)

#### TSK-004: Git Operations Module (pygit2)
- **Description**: Wrapper for cloning public/private repositories and identifying changed files.
- **Dependencies**: TSK-001
- **Files**:
  - `[NEW] gitreverse/git/__init__.py`
  - `[NEW] gitreverse/git/clone.py`
  - `[NEW] gitreverse/git/diff.py`
  - `[NEW] gitreverse/git/auth.py`
- **Acceptance Criteria**:
  - `clone_repository` clones public and private repos (using personal access token).
  - `get_changed_files` takes two commit hashes and returns correct modified file list using `pygit2.diff`.

#### TSK-005: Tree-Sitter Parser Builder
- **Description**: Build and load tree-sitter grammar libraries dynamically on demand.
- **Dependencies**: TSK-001
- **Files**:
  - `[NEW] gitreverse/parsers/__init__.py`
  - `[NEW] gitreverse/parsers/base.py`
  - `[NEW] gitreverse/parsers/treesitter_parser.py`
- **Acceptance Criteria**:
  - Compiles vendor grammar sources (`.so` / `.dll`) when parser starts.
  - Dynamically switches parser languages based on target file extensions.

#### TSK-006: Language AST Parsers (Python & JavaScript/TypeScript)
- **Description**: Implement specific parsers extracting imports and symbol definitions (classes, functions).
- **Dependencies**: TSK-005
- **Files**:
  - `[NEW] gitreverse/parsers/languages/python.py`
  - `[NEW] gitreverse/parsers/languages/javascript.py`
- **Acceptance Criteria**:
  - Parsing a Python file correctly extracts functions, classes, and import declarations with line ranges.
  - Parsing a JavaScript/TypeScript file correctly extracts symbols and import trees.

---

### Phase 3: Analyzers & Graph Queries

#### TSK-007: Manifest Dependency Analyzer
- **Description**: Parse package manifests (`package.json`, `requirements.txt`, etc.) to extract libraries and version ranges.
- **Dependencies**: TSK-002, TSK-003
- **Files**:
  - `[NEW] gitreverse/analyzers/__init__.py`
  - `[NEW] gitreverse/analyzers/base.py`
  - `[NEW] gitreverse/analyzers/dependency_analyzer.py`
- **Acceptance Criteria**:
  - Correctly parses an Express.js `package.json` and records runtime dependencies in `dependency` table.
  - Correctly parses Python `requirements.txt`.

#### TSK-008: Framework Detection Analyzer
- **Description**: Inspect imports and package versions to detect the underlying framework.
- **Dependencies**: TSK-006, TSK-007
- **Files**:
  - `[NEW] gitreverse/analyzers/framework_detector.py`
- **Acceptance Criteria**:
  - Detects "React" or "FastAPI" and builds a JSON payload outlining evidence (imports found, files, versions).

#### TSK-009: Knowledge Graph Edges & Traversals
- **Description**: Construct AST symbol call graphs and run recursive CTE traversals.
- **Dependencies**: TSK-003, TSK-008
- **Files**:
  - `[NEW] gitreverse/storage/queries.py` (updates)
- **Acceptance Criteria**:
  - `get_downstream_dependencies` outputs a recursive sequence of caller symbols.
  - SQL traversals perform under 100ms for test graphs containing up to 10k nodes/edges.

---

### Phase 4: Integration & Execution

#### TSK-010: Pipeline Orchestrator
- **Description**: Chain cloning, file listing, language parsing, analyzers, and storage operations.
- **Dependencies**: TSK-003, TSK-004, TSK-006, TSK-007, TSK-008, TSK-009
- **Files**:
  - `[NEW] gitreverse/core/pipeline.py`
  - `[NEW] gitreverse/core/context.py`
- **Acceptance Criteria**:
  - Orchestrator accepts a repo URL, processes it asynchronously, and updates progress indicators.
  - Handles task cancellation cleanly, killing sub-tasks without corrupting local SQLite or leaving orphaned git folders.

#### TSK-011: Textual TUI Application Layout & Interaction
- **Description**: Build the Textual TUI (Terminal User Interface) layout with widgets for URL input, dynamic analysis progress, and query output panels.
- **Dependencies**: TSK-010
- **Files**:
  - `[NEW] gitreverse/cli/app.py`
  - `[NEW] gitreverse/cli/views/main.py`
  - `[NEW] gitreverse/cli/views/progress.py`
  - `[NEW] gitreverse/cli/views/results.py`
- **Acceptance Criteria**:
  - Launching the app via `gitreverse` loads a Textual TUI containing an input area, results area, and a persistent status bar indicating mode, model, and active repository (satisfying Principle V).
  - Pasting a repository URL and hitting Enter runs the asynchronous analysis pipeline.
  - Multi-stage progress indicators (Clone, AST Parse, Analyze, Graph Build) update dynamically in the TUI without freezing the interface.
  - Query submissions stream markdown outputs in the results viewport.

