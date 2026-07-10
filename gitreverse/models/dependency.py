from sqlmodel import SQLModel, Field

class Dependency(SQLModel, table=True):
    __tablename__ = "dependency"
    id: int | None = Field(default=None, primary_key=True)
    repository_id: int = Field(foreign_key="repository.id", ondelete="CASCADE", index=True)
    package_name: str
    version: str | None = None
    source_file: str
    type: str  # runtime, dev, peer
