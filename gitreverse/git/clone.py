import subprocess
from pathlib import Path
from gitreverse.utils.logging import get_logger

logger = get_logger("git.clone")

def clone_repository(url: str, dest_path: Path, token: str | None = None) -> Path:
    """Clone using system git CLI for maximum compatibility (HTTPS, SSH, proxies)."""
    logger.info(f"Cloning repository {url} to {dest_path}")
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    # If already cloned, pull latest instead
    if (dest_path / ".git").exists():
        logger.info(f"Repository already cloned at {dest_path}, fetching updates.")
        result = subprocess.run(
            ["git", "-C", str(dest_path), "fetch", "--all"],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            logger.warning(f"git fetch warning: {result.stderr}")
        return dest_path

    # Inject token into URL for private repos
    clone_url = url
    if token:
        # https://token@github.com/user/repo
        clone_url = url.replace("https://", f"https://{token}@")

    result = subprocess.run(
        ["git", "clone", "--depth", "1", clone_url, str(dest_path)],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        err = result.stderr.strip()
        logger.error(f"git clone failed: {err}")
        raise RuntimeError(f"Clone failed: {err}")

    logger.info(f"Successfully cloned {url}")
    return dest_path

