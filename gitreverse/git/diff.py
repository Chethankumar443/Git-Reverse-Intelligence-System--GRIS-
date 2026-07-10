import pygit2
from pathlib import Path
from typing import List
from gitreverse.utils.logging import get_logger

logger = get_logger("git.diff")

def get_current_commit_hash(repo_path: Path) -> str:
    repo = pygit2.Repository(str(repo_path))
    return str(repo.head.target)

def should_reanalyze(repo_path: Path, cached_hash: str) -> bool:
    current_hash = get_current_commit_hash(repo_path)
    return current_hash != cached_hash

def get_changed_files(repo_path: Path, old_hash: str, new_hash: str) -> List[Path]:
    repo = pygit2.Repository(str(repo_path))
    old_commit = repo.get(old_hash)
    new_commit = repo.get(new_hash)
    
    if not old_commit or not new_commit:
        logger.warning(f"Could not find commits {old_hash} or {new_hash} to diff.")
        return []
        
    diff = repo.diff(old_commit, new_commit)
    changed_files = []
    for patch in diff:
        # relative path from repo root
        changed_files.append(Path(patch.delta.new_file.path))
        
    return changed_files
