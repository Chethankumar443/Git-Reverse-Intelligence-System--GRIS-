from datetime import datetime
from sqlmodel import SQLModel, Field

class File(SQLModel, table=True):
    __tablename__ = "file"
    id: int | None = Field(default=None, primary_key=True)
    repository_id: int = Field(foreign_key="repository.id", ondelete="CASCADE", index=True)
    path: str = Field(index=True)
    language: str
    size_bytes: int
    last_modified: datetime
    ast_hash: str
