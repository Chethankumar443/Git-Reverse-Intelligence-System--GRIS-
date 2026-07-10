# Feature Specification: Repository Analysis Pipeline

**Feature Branch**: `001-repository-analysis-pipeline`
**Created**: 2026-07-10
**Status**: Draft
**Input**: User description: "Build the core pipeline that clones a GitHub repository, analyzes its structure using AST parsers, extracts dependencies, builds architecture graphs, and produces a knowledge graph that can be queried by the LLM reasoning layer."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Clone and Analyze Public Repository (Priority: P1)
A developer pastes a public GitHub URL (e.g., https://github.com/facebook/react). The system clones the repository, runs the full analysis pipeline, and produces a structured knowledge graph. The developer can then ask questions like "Explain the architecture" or "Generate a reconstruction prompt" and receive evidence-backed answers.

**Why this priority**: This is the core value proposition. Without this, nothing else works.

**Independent Test**: Can be tested by cloning a small public repo (<10k LOC), verifying the knowledge graph is generated, and querying it for architecture explanation. Delivers immediate value: user understands a foreign codebase in seconds.

**Acceptance Scenarios**:
1. **Given** a valid public GitHub URL, **When** user runs `analyze <url>`, **Then** system clones repo, runs analysis, and displays progress indicators for each stage (clone, parse, dependency analysis, architecture extraction, knowledge graph construction).
2. **Given** analysis is complete, **When** user asks "What framework does this use?", **Then** system responds with evidence: "This project uses React 18.2.0 (source: package.json line 42). The primary state management is Redux (source: src/store/index.ts imports createStore from redux)."
3. **Given** analysis is complete, **When** user runs `prompt generate`, **Then** system produces a reconstruction prompt that includes: detected technologies, folder structure, key patterns, dependencies, and architectural decisions—with citations to source files.

---

### User Story 2 - Handle Private Repositories (Priority: P2)
A developer wants to analyze a private repository. They provide a GitHub Personal Access Token (PAT) via secure input. The system uses the token to clone the private repo and runs the same analysis pipeline. The token is stored securely (OS keychain or encrypted config) and never logged or transmitted except to GitHub API.

**Why this priority**: Critical for real-world usage, but not needed for initial public-repo-only MVP.

**Independent Test**: Can be tested by creating a private test repo, providing PAT, and verifying successful clone + analysis.

**Acceptance Scenarios**:
1. **Given** user has a private repo, **When** they run `analyze <private-url> --token`, **Then** system prompts for PAT securely (no echo), validates it against GitHub API, clones repo, and proceeds with analysis.
2. **Given** PAT is stored, **When** user runs `analyze <same-private-url>`, **Then** system reuses stored token without re-prompting.
3. **Given** PAT is invalid, **When** user attempts clone, **Then** system displays clear error: "GitHub authentication failed. Token may be expired or lack repo scope."

---

### User Story 3 - Incremental Re-Analysis (Priority: P3)
A developer has already analyzed a repository. They pull new changes (git pull) and want to re-analyze only the changed files, not the entire repository. The system detects changed files via git diff, re-runs analysis only on those files, and updates the knowledge graph incrementally.

**Why this priority**: Performance optimization for large repos. Not critical for MVP but important for daily-driver usage.

**Independent Test**: Can be tested by analyzing a repo, making a commit that changes 3 files, running re-analyze, and verifying only those 3 files were re-parsed.

**Acceptance Scenarios**:
1. **Given** a previously analyzed repository, **When** user runs `analyze --incremental`, **Then** system runs `git diff HEAD~1` (or since last analysis), identifies changed files, re-parses only those files, and updates knowledge graph.
2. **Given** incremental analysis, **When** user queries architecture, **Then** response reflects updated state, not stale data.

---

### Edge Cases
- What happens when repository is empty (no files)? → Display error: "Repository contains no analyzable files."
- What happens when repository has unsupported language (e.g., COBOL)? → Skip AST parsing for unsupported files, but still analyze package.json, README, etc. Display warning: "AST parsing skipped for 15 files in unsupported languages."
- What happens when repository is massive (>1M LOC)? → Stream analysis progress, allow cancellation, cache intermediate results to disk, resume on restart.
- What happens when GitHub API rate limit is hit? → Display clear error with retry-after time, suggest using PAT for higher limits.
- What happens when network fails mid-clone? → Retry with exponential backoff, preserve partial clone if possible, allow resume.

## Requirements *(mandatory)*

### Functional Requirements
- **FR-001**: System MUST clone GitHub repositories (public and private with PAT) to a local cache directory.
- **FR-002**: System MUST detect programming languages present in the repository using file extensions and content analysis.
- **FR-003**: System MUST parse source files using tree-sitter AST parsers for supported languages (JavaScript, TypeScript, Python, Rust, Go, Java, C++, C#).
- **FR-004**: System MUST extract symbols: functions, classes, methods, variables, imports, exports.
- **FR-005**: System MUST build dependency graphs from package manifests (package.json, requirements.txt, Cargo.toml, go.mod, pom.xml, etc.).
- **FR-006**: System MUST detect frameworks by analyzing imports, configuration files, and directory structure.
- **FR-007**: System MUST construct architecture graphs showing module relationships, data flow, and layer boundaries.
- **FR-008**: System MUST build a knowledge graph combining all extracted information with relationships and metadata.
- **FR-009**: System MUST persist analysis results to local SQLite database for fast querying.
- **FR-010**: System MUST provide a query interface for the LLM to retrieve structured knowledge.
- **FR-011**: System MUST display real-time progress indicators during analysis (clone %, parse %, graph construction %).
- **FR-012**: System MUST support cancellation of long-running analysis tasks.
- **FR-013**: System MUST cache analysis results and support incremental re-analysis.
- **FR-014**: System MUST handle repositories with multiple languages and monorepo structures.
- **FR-015**: System MUST generate citations for every claim (file path, line number, symbol name).

### Key Entities
- **Repository**: URL, local path, clone date, last analysis date, size, language breakdown, branch info.
- **File**: Path, language, size, last modified, AST hash (for change detection).
- **Symbol**: Name, kind (function/class/variable), file path, line range, dependencies, dependents.
- **Dependency**: Package name, version, source file, type (runtime/dev/peer).
- **Framework**: Name, version, detection evidence (files, imports, config).
- **ArchitectureNode**: Module name, type (layer/component/service), files contained.
- **ArchitectureEdge**: Source node, target node, relationship type (imports/calls/depends-on).
- **KnowledgeGraph**: Composite of all above entities with relationships.

## Success Criteria *(mandatory)*

### Measurable Outcomes
- **SC-001**: System can clone and fully analyze a 10k LOC repository in <60 seconds on a modern laptop (M1 Mac or equivalent).
- **SC-002**: Knowledge graph queries return results in <100ms for repositories <100k LOC.
- **SC-003**: LLM responses include citations in 100% of cases (verified by automated test).
- **SC-004**: System correctly identifies the primary framework in 95% of test repositories (measured against a benchmark suite of 50 repos).
- **SC-005**: Incremental re-analysis processes only changed files and completes in <10s for typical commits (<10 files changed).
- **SC-006**: Memory usage stays <500MB for repositories <100k LOC.
- **SC-007**: System handles 10 concurrent analysis tasks without degradation (for future server mode).
- **SC-008**: User can generate a reconstruction prompt that includes all detected technologies, folder structure, and key patterns within 5 seconds of analysis completion.

## Assumptions
- Users have git installed and configured on their machine.
- Users have Python 3.11+ installed (for V1).
- Public repositories are accessible without authentication (subject to GitHub rate limits: 60 requests/hour unauthenticated, 5000/hour with PAT).
- tree-sitter grammars for target languages are available and stable.
- Users understand that analysis quality depends on repository structure (well-organized repos yield better results).
- V1 targets macOS and Linux; Windows support is V1.1.
- OpenRouter API key is provided by user (not bundled with app).
- Repositories >1M LOC may require manual optimization or chunked analysis (out of scope for V1).
