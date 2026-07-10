import pygit2
from pathlib import Path
from gitreverse.utils.logging import get_logger
from gitreverse.git.auth import get_callbacks

logger = get_logger("git.clone")

def clone_repository(url: str, dest_path: Path, token: str | None = None) -> pygit2.Repository:
    logger.info(f"Cloning repository {url} to {dest_path}")
    callbacks = get_callbacks(token)
    
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        repo = pygit2.clone_repository(
            url,
            str(dest_path),
            callbacks=callbacks
        )
        logger.info(f"Successfully cloned repository {url}")
        return repo
    except Exception as e:
        logger.error(f"Failed to clone repository {url}: {e}")
        raise
