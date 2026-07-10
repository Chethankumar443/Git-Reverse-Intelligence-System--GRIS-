import logging
from pathlib import Path
from gitreverse.utils.config import DEFAULT_CONFIG_DIR

DEFAULT_LOG_PATH = DEFAULT_CONFIG_DIR / "gitreverse.log"

def setup_logging(level: int = logging.INFO) -> None:
    DEFAULT_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    
    logger = logging.getLogger("gitreverse")
    logger.setLevel(level)
    
    if logger.handlers:
        return
        
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # File Handler - critical for TUI to avoid corrupting stdout/stderr
    file_handler = logging.FileHandler(DEFAULT_LOG_PATH, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(f"gitreverse.{name}")
