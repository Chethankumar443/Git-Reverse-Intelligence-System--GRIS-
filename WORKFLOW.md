# Git Reverse — Development Orchestration Workflow

## Phase 0: Research ✅ COMPLETE
**Artifact**: `research.md` (locked technical decisions)
**Status**: All unknowns resolved. Stack locked.

## Phase 1: Design (CURRENT)
**Goal**: Generate data model, interface contracts, quickstart validation.

**Steps**:
1. Feed `CONTEXT.md` + `research.md` to AI agent.
2. Prompt: "Generate `data-model.md` with all entities, relationships, and schema."
3. Review data model. Validate against constitution (especially Principle II: Analysis Before Reasoning).
4. Prompt: "Generate interface contracts for analyzers, parsers, and storage."
5. Review contracts. Validate plugin architecture (Principle IV).
6. Prompt: "Generate `quickstart.md` with end-to-end validation scenario."
7. Run quickstart manually. Confirm it works before proceeding.

**Gate**: Quickstart passes. Data model and contracts approved.

## Phase 2: Tasks
**Goal**: Break plan into dependency-ordered implementation tasks.

**Steps**:
1. Feed `CONTEXT.md` + `research.md` + Phase 1 artifacts to AI agent.
2. Prompt: "Generate `tasks.md` with dependency-ordered tasks. Each task must be independently testable."
3. Review task list. Validate:
   - No task depends on unimplemented future work
   - Each task has clear acceptance criteria
   - Tasks are ordered by dependency (foundations first)
4. Validate task count is manageable (<50 tasks per batch).

**Gate**: Task list approved. No circular dependencies.

## Phase 3: Implementation
**Goal**: Execute tasks via coding agent.

**Steps**:
1. Feed `CONTEXT.md` + `tasks.md` to coding agent (Claude Code, Copilot, etc.).
2. Agent implements tasks in order.
3. After each task: run tests, validate acceptance criteria.
4. If task fails: diagnose, fix, re-run. Do not proceed until green.
5. After all tasks: run full integration test suite.

**Gate**: All tests pass. Quickstart scenario works end-to-end.

## Phase 4: Packaging & Release
**Goal**: Package as standalone binary, prepare for distribution.

**Steps**:
1. Configure PyInstaller/Nuitka for standalone binary.
2. Test binary on clean machine (no Python installed).
3. Set up CI/CD for automated builds.
4. Publish to PyPI, Homebrew, Winget, Scoop.

**Gate**: Binary installs and runs on fresh macOS, Linux, Windows machines.
