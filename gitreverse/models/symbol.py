from sqlmodel import SQLModel, Field

class Symbol(SQLModel, table=True):
    __tablename__ = "symbol"
    id: int | None = Field(default=None, primary_key=True)
    file_id: int = Field(foreign_key="file.id", ondelete="CASCADE", index=True)
    name: str = Field(index=True)
    kind: str  # function, class, method, variable, import, export
    line_start: int
    line_end: int
