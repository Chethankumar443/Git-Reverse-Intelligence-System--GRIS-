from sqlmodel import SQLModel, Field, JSON
from sqlalchemy import Column

class Framework(SQLModel, table=True):
    __tablename__ = "framework"
    id: int | None = Field(default=None, primary_key=True)
    repository_id: int = Field(foreign_key="repository.id", ondelete="CASCADE", index=True)
    name: str
    version: str | None = None
    evidence: dict | None = Field(default=None, sa_column=Column(JSON))
