import os
import sqlite3
from typing import Any, List, Optional
from pathlib import Path
from datetime import datetime
from sqlmodel import SQLModel, create_engine, Session, select
from gitreverse.utils.config import load_config
from gitreverse.utils.logging import get_logger
from gitreverse.models import Repository, File, Symbol, Dependency, Framework, KnowledgeGraph

logger = get_logger("storage")

class DatabaseManager:
    def __init__(self, db_path: str | None = None):
        if db_path is None:
            config = load_config()
            db_path = config.database.db_path
            
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        db_url = f"sqlite:///{self.db_path}"
        self.engine = create_engine(
            db_url,
            connect_args={"check_same_thread": False},
            pool_size=10,
            pool_pre_ping=True
        )
        
        self.init_db()
        self.enable_wal()

    def init_db(self) -> None:
        """Create all SQLModel tables."""
        logger.info(f"Initializing database at {self.db_path}")
        SQLModel.metadata.create_all(self.engine)

    def enable_wal(self) -> None:
        """Configure SQLite WAL mode for concurrency."""
        with self.engine.connect() as conn:
            conn.exec_driver_sql("PRAGMA journal_mode=WAL")
            conn.exec_driver_sql("PRAGMA synchronous=NORMAL")
            conn.exec_driver_sql("PRAGMA cache_size=10000")
            logger.info("SQLite WAL mode activated.")

    def get_session(self) -> Session:
        return Session(self.engine)

    # --- Storage Contract Implementation ---

    def save_repository(self, url: str, local_path: str, commit_hash: str, size_bytes: int) -> int:
        with self.get_session() as session:
            statement = select(Repository).where(Repository.url == url)
            repo = session.exec(statement).first()
            if repo:
                repo.local_path = local_path
                repo.commit_hash = commit_hash
                repo.size_bytes = size_bytes
                repo.last_analysis_date = datetime.utcnow()
            else:
                repo = Repository(
                    url=url,
                    local_path=local_path,
                    commit_hash=commit_hash,
                    size_bytes=size_bytes
                )
                session.add(repo)
            
            session.commit()
            session.refresh(repo)
            return repo.id

    def get_repository(self, repo_id: int) -> Optional[dict]:
        with self.get_session() as session:
            repo = session.get(Repository, repo_id)
            return repo.model_dump() if repo else None

    def bulk_save_files(self, repo_id: int, files: List[dict]) -> None:
        with self.get_session() as session:
            for f_data in files:
                statement = select(File).where(
                    File.repository_id == repo_id,
                    File.path == f_data["path"]
                )
                db_file = session.exec(statement).first()
                if db_file:
                    for k, v in f_data.items():
                        setattr(db_file, k, v)
                else:
                    db_file = File(repository_id=repo_id, **f_data)
                    session.add(db_file)
            session.commit()

    def bulk_save_symbols(self, symbols: List[dict]) -> None:
        with self.get_session() as session:
            for s_data in symbols:
                db_symbol = Symbol(**s_data)
                session.add(db_symbol)
            session.commit()

    def save_framework_evidence(self, repo_id: int, name: str, evidence: dict) -> None:
        with self.get_session() as session:
            statement = select(Framework).where(
                Framework.repository_id == repo_id,
                Framework.name == name
            )
            fw = session.exec(statement).first()
            if fw:
                fw.evidence = evidence
                fw.version = evidence.get("version")
            else:
                fw = Framework(
                    repository_id=repo_id,
                    name=name,
                    version=evidence.get("version"),
                    evidence=evidence
                )
                session.add(fw)
            session.commit()

    def add_edges(self, edges: List[dict]) -> None:
        with self.get_session() as session:
            for edge_data in edges:
                # Remap 'metadata' key to 'edge_metadata' to avoid SQLAlchemy conflict
                if "metadata" in edge_data:
                    edge_data["edge_metadata"] = edge_data.pop("metadata")
                edge = KnowledgeGraph(**edge_data)
                session.add(edge)
            session.commit()

    def get_downstream_dependencies(self, symbol_id: int, max_depth: int = 10) -> List[dict]:
        sql = """
        WITH RECURSIVE downstream_calls AS (
            SELECT target_id, target_type, 1 AS depth
            FROM knowledge_graph
            WHERE source_id = :symbol_id AND source_type = 'symbol' AND relationship = 'calls'
            
            UNION ALL
            
            SELECT kg.target_id, kg.target_type, dc.depth + 1
            FROM knowledge_graph kg
            JOIN downstream_calls dc ON kg.source_id = dc.target_id AND kg.source_type = dc.target_type
            WHERE kg.relationship = 'calls' AND dc.depth < :max_depth
        )
        SELECT s.*, dc.depth
        FROM symbol s
        JOIN downstream_calls dc ON s.id = dc.target_id AND dc.target_type = 'symbol'
        ORDER BY dc.depth ASC;
        """
        return self.raw_query(sql, {"symbol_id": symbol_id, "max_depth": max_depth})

    def raw_query(self, sql: str, params: dict) -> List[dict]:
        with self.engine.connect() as conn:
            from sqlalchemy import text
            result = conn.execute(text(sql), params)
            return [dict(row._mapping) for row in result]
