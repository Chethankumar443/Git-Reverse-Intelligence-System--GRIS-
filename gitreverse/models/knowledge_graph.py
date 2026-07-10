from sqlmodel import SQLModel, Field, JSON
from sqlalchemy import Column

class KnowledgeGraph(SQLModel, table=True):
    __tablename__ = "knowledge_graph"
    id: int | None = Field(default=None, primary_key=True)
    source_id: int = Field(index=True)
    source_type: str = Field(index=True)  # symbol, file, repository
    target_id: int = Field(index=True)
    target_type: str = Field(index=True)  # symbol, file, repository
    relationship: str = Field(index=True)  # calls, imports, contains, etc
    edge_metadata: dict | None = Field(default=None, sa_column=Column(JSON))
