# Phase 1: Quickstart Validation Scenario

**Goal**: Validate the core technology stack (SQLite + SQLModel, pygit2, tree-sitter) on the user's local machine before proceeding to implementation tasks. This proves our Phase 0 research decisions are viable in practice.

## Prerequisites Setup

1. **Install Python dependencies**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install sqlmodel pygit2 tree-sitter pydantic
   ```

2. **Clone Tree-Sitter Python Grammar**:
   We need a sample grammar to test parsing.
   ```bash
   git clone https://github.com/tree-sitter/tree-sitter-python vendor/tree-sitter-python
   ```

## Validation Script (`validate_stack.py`)

Create this script in the root directory to test our three core pillars:
1. **Git Operations (pygit2)**: Can we clone a repo?
2. **AST Parsing (tree-sitter)**: Can we compile a grammar and parse a file?
3. **Database (SQLModel)**: Can we initialize SQLite in WAL mode?

```python
import os
import shutil
from pathlib import Path
import pygit2
import tree_sitter
from tree_sitter import Language, Parser
from sqlmodel import SQLModel, Field, create_engine, Session

# 1. Database Model
class TestRepo(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    url: str
    commit_hash: str

def main():
    print("--- 1. Testing Database (SQLModel + SQLite WAL) ---")
    db_path = "test_cache.db"
    engine = create_engine(f"sqlite:///{db_path}")
    SQLModel.metadata.create_all(engine)
    
    with engine.connect() as conn:
        conn.execute("PRAGMA journal_mode=WAL")
    
    print("✓ SQLite initialized in WAL mode.")

    print("\n--- 2. Testing Git Operations (pygit2) ---")
    repo_url = "https://github.com/expressjs/express"
    clone_dir = "test_express_clone"
    
    if os.path.exists(clone_dir):
        shutil.rmtree(clone_dir)
        
    print(f"Cloning {repo_url}...")
    repo = pygit2.clone_repository(repo_url, clone_dir)
    head_commit = str(repo.head.target)
    print(f"✓ Cloned successfully. HEAD commit: {head_commit[:8]}")

    with Session(engine) as session:
        db_repo = TestRepo(url=repo_url, commit_hash=head_commit)
        session.add(db_repo)
        session.commit()
        print("✓ Saved repo metadata to SQLite.")

    print("\n--- 3. Testing AST Parsing (tree-sitter) ---")
    if not os.path.exists("vendor/tree-sitter-python"):
        print("❌ Skipping tree-sitter test: vendor/tree-sitter-python not found.")
        print("Run: git clone https://github.com/tree-sitter/tree-sitter-python vendor/tree-sitter-python")
    else:
        Language.build_library(
            'build/languages.so',
            ['vendor/tree-sitter-python']
        )
        PYTHON_LANGUAGE = Language('build/languages.so', 'python')
        parser = Parser()
        parser.set_language(PYTHON_LANGUAGE)
        
        sample_code = b"def test_func():\n    return 'Hello World'"
        tree = parser.parse(sample_code)
        print(f"✓ Parsed python code. Root node: {tree.root_node.type}")

    print("\n✅ All stack validation tests passed.")

if __name__ == "__main__":
    main()
```

## Running the Validation

Run the script manually to confirm your local environment supports the chosen stack:
```bash
python validate_stack.py
```

**Gate**: Once this script runs successfully and outputs `✅ All stack validation tests passed.`, Phase 1 is officially complete and we can proceed to Phase 2 (Tasks).
