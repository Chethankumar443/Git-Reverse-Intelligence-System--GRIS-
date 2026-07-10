from datetime import datetime
from sqlmodel import SQLModel, Field

class Repository(SQLModel, table=True):
    __tablename__ = "repository"
    id: int | None = Field(default=None, primary_key=True)
    url: str = Field(unique=True, index=True)
    local_path: str
    clone_date: datetime = Field(default_factory=datetime.utcnow)
    last_analysis_date: datetime = Field(default_factory=datetime.utcnow)
    commit_hash: str
    size_bytes: int
