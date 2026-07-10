import os
import toml
from pathlib import Path
from pydantic import BaseModel, Field

DEFAULT_CONFIG_DIR = Path("~/.gitreverse").expanduser()
DEFAULT_CONFIG_PATH = DEFAULT_CONFIG_DIR / "config.toml"

class AnalysisConfig(BaseModel):
    max_concurrent_tasks: int = Field(default=5, ge=1, le=20)
    memory_limit_mb: int = Field(default=500, ge=100)

class DatabaseConfig(BaseModel):
    db_path: str = Field(default=str(DEFAULT_CONFIG_DIR / "cache.db"))

class GitReverseConfig(BaseModel):
    analysis: AnalysisConfig = Field(default_factory=AnalysisConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)

def load_config() -> GitReverseConfig:
    if not DEFAULT_CONFIG_PATH.exists():
        DEFAULT_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        default_config = GitReverseConfig()
        with open(DEFAULT_CONFIG_PATH, "w") as f:
            toml.dump(default_config.model_dump(), f)
        return default_config
    
    try:
        data = toml.load(DEFAULT_CONFIG_PATH)
        return GitReverseConfig.model_validate(data)
    except Exception as e:
        # Fallback to defaults
        print(f"Warning: Failed to load config from {DEFAULT_CONFIG_PATH}: {e}. Using defaults.")
        return GitReverseConfig()

if __name__ == "__main__":
    config = load_config()
    print("Loaded configuration successfully:")
    print(config.model_dump_json(indent=2))
