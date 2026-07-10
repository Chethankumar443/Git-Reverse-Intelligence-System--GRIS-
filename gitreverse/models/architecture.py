from sqlmodel import SQLModel, Field

class ArchitectureNode(SQLModel, table=True):
    __tablename__ = "architecture_node"
    id: int | None = Field(default=None, primary_key=True)
    repository_id: int = Field(foreign_key="repository.id", ondelete="CASCADE", index=True)
    name: str
    node_type: str  # layer, component, service

class ArchitectureEdge(SQLModel, table=True):
    __tablename__ = "architecture_edge"
    id: int | None = Field(default=None, primary_key=True)
    source_node_id: int = Field(foreign_key="architecture_node.id", ondelete="CASCADE", index=True)
    target_node_id: int = Field(foreign_key="architecture_node.id", ondelete="CASCADE", index=True)
    relationship_type: str
