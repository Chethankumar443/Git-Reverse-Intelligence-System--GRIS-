import datetime
import json
import os
from typing import List, Optional, Dict, Any
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Float, event, text
from sqlalchemy.orm import declarative_base, sessionmaker, Session as SASession

Base = declarative_base()

ANALYZER_VERSION = "1.1.0"


class SessionRecord(Base):
    __tablename__ = "session_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    repo_url = Column(String(512), nullable=False)
    repo_name = Column(String(256), nullable=False)
    language = Column(String(64), default="Unknown")
    file_count = Column(Integer, default=0)
    generated_prompt = Column(Text, default="")
    model_used = Column(String(128), default="gpt-4o")
    source_license = Column(String(64), default="none")
    created_at = Column(DateTime, default=datetime.datetime.now)
    status = Column(String(32), default="pending")
    # §50 Repository Version Tracking
    commit_sha = Column(String(64), default="")
    branch = Column(String(128), default="")
    repo_tag = Column(String(64), default="")
    analyzer_version = Column(String(32), default=ANALYZER_VERSION)
    # §53 Secret detection count
    secret_warnings = Column(Integer, default=0)
    # §51 KB versioning
    version_number = Column(Integer, default=1)
    kb_history = Column(Text, default="[]")  # JSON array of prior version summaries
    code_symbols = Column(Text, default="")  # Raw AST symbols with line numbers

    def to_dict(self):
        return {
            "id": self.id,
            "repo_url": self.repo_url,
            "repo_name": self.repo_name,
            "language": self.language,
            "file_count": self.file_count,
            "generated_prompt": self.generated_prompt,
            "model_used": self.model_used,
            "source_license": self.source_license,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else "",
            "status": self.status,
            "commit_sha": self.commit_sha or "",
            "branch": self.branch or "",
            "repo_tag": self.repo_tag or "",
            "analyzer_version": self.analyzer_version or ANALYZER_VERSION,
            "secret_warnings": self.secret_warnings or 0,
            "version_number": self.version_number or 1,
            "kb_history": json.loads(self.kb_history or "[]"),
            "code_symbols": self.code_symbols or "",
        }


class SpendingLog(Base):
    """Tracks LLM token usage per day for spending protection (PRD §64)."""
    __tablename__ = "spending_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date_str = Column(String(10), nullable=False)        # YYYY-MM-DD
    tokens_used = Column(Integer, default=0)
    estimated_cost_usd = Column(Float, default=0.0)
    provider = Column(String(64), default="")
    model_id = Column(String(128), default="")


def get_db_filepath() -> str:
    appdata = os.getenv("APPDATA") or os.path.expanduser("~")
    db_dir = os.path.join(appdata, "GitReverse")
    os.makedirs(db_dir, exist_ok=True)
    return os.path.join(db_dir, "git_reverse.db")


class DatabaseManager:
    """Production SQLite Database Manager using SQLAlchemy ORM with WAL mode

    and FTS5 Full-Text Search indexing per trd.md §4.
    Extended with version tracking (§50), KB history (§51), spending log (§64).
    """

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            db_path = get_db_filepath()

        self.db_path = db_path
        self.engine = create_engine(
            f"sqlite:///{self.db_path}",
            connect_args={"timeout": 30},
            echo=False,
        )

        # Enable WAL mode and FTS5 for SQLite
        @event.listens_for(self.engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA busy_timeout=5000")
            cursor.close()

        Base.metadata.create_all(self.engine)
        self._migrate_schema()
        self.init_fts5_index()
        self.SessionLocal = sessionmaker(bind=self.engine)

    def _migrate_schema(self):
        """Adds any missing columns to existing database (safe migration)."""
        new_columns = [
            ("commit_sha", "TEXT DEFAULT ''"),
            ("branch", "TEXT DEFAULT ''"),
            ("repo_tag", "TEXT DEFAULT ''"),
            ("analyzer_version", "TEXT DEFAULT '1.0.0'"),
            ("secret_warnings", "INTEGER DEFAULT 0"),
            ("version_number", "INTEGER DEFAULT 1"),
            ("kb_history", "TEXT DEFAULT '[]'"),
            ("code_symbols", "TEXT DEFAULT ''"),
        ]
        with self.engine.connect() as conn:
            for col_name, col_def in new_columns:
                try:
                    conn.execute(text(f"ALTER TABLE session_records ADD COLUMN {col_name} {col_def};"))
                    conn.commit()
                except Exception:
                    pass  # Column already exists

    def init_fts5_index(self):
        """Creates SQLite FTS5 Virtual Table for full-text search if supported."""
        with self.engine.connect() as conn:
            try:
                conn.execute(text("""
                    CREATE VIRTUAL TABLE IF NOT EXISTS session_records_fts USING fts5(
                        repo_name,
                        generated_prompt,
                        source_license,
                        code_symbols,
                        content='session_records',
                        content_rowid='id'
                    );
                """))
                conn.commit()
            except Exception:
                pass

    def create_session(
        self,
        repo_url: str,
        repo_name: str,
        language: str = "Unknown",
        file_count: int = 0,
        source_license: str = "none",
        model_used: str = "gpt-4o",
        commit_sha: str = "",
        branch: str = "",
        repo_tag: str = "",
        secret_warnings: int = 0,
    ) -> "SessionRecord":
        db: SASession = self.SessionLocal()
        try:
            record = SessionRecord(
                repo_url=repo_url,
                repo_name=repo_name,
                language=language,
                file_count=file_count,
                source_license=source_license,
                model_used=model_used,
                status="analyzing",
                commit_sha=commit_sha,
                branch=branch,
                repo_tag=repo_tag,
                analyzer_version=ANALYZER_VERSION,
                secret_warnings=secret_warnings,
                version_number=1,
                kb_history="[]",
                code_symbols="",
            )
            db.add(record)
            db.commit()
            db.refresh(record)
            return record
        finally:
            db.close()

    def update_session_prompt(
        self,
        session_id: int,
        prompt: str,
        status: str = "complete",
        secret_warnings: int = 0,
        code_symbols: str = "",
    ) -> bool:
        db: SASession = self.SessionLocal()
        try:
            record = db.query(SessionRecord).filter(SessionRecord.id == session_id).first()
            if record:
                # §51 KB versioning: push current prompt to history before overwriting
                if record.generated_prompt and record.generated_prompt != prompt:
                    try:
                        history = json.loads(record.kb_history or "[]")
                    except Exception:
                        history = []
                    history.append({
                        "version": record.version_number or 1,
                        "date": record.created_at.strftime("%Y-%m-%d %H:%M") if record.created_at else "",
                        "prompt_excerpt": record.generated_prompt[:200],
                    })
                    record.kb_history = json.dumps(history[-10:])  # Keep last 10 versions
                    record.version_number = (record.version_number or 1) + 1

                record.generated_prompt = prompt
                record.status = status
                if secret_warnings:
                    record.secret_warnings = secret_warnings
                if code_symbols:
                    record.code_symbols = code_symbols
                db.commit()

                # Sync to FTS5 index (INSERT OR REPLACE)
                try:
                    db.execute(text("""
                        INSERT OR REPLACE INTO session_records_fts(rowid, repo_name, generated_prompt, source_license, code_symbols)
                        VALUES (:id, :name, :prompt, :license, :symbols);
                    """), {
                        "id": record.id,
                        "name": record.repo_name,
                        "prompt": prompt,
                        "license": record.source_license,
                        "symbols": record.code_symbols or ""
                    })
                    db.commit()
                except Exception:
                    pass

                return True
            return False
        finally:
            db.close()

    def get_all_sessions(self) -> List["SessionRecord"]:
        db: SASession = self.SessionLocal()
        try:
            return db.query(SessionRecord).order_by(SessionRecord.id.desc()).all()
        finally:
            db.close()

    def search_sessions(self, query_str: str) -> List["SessionRecord"]:
        """Searches sessions using FTS5 MATCH full-text index with LIKE fallback."""
        clean_q = query_str.strip()
        if not clean_q:
            return self.get_all_sessions()

        db: SASession = self.SessionLocal()
        try:
            # Try FTS5 MATCH query first
            try:
                fts_res = db.execute(text("""
                    SELECT content_rowid FROM session_records_fts
                    WHERE session_records_fts MATCH :q
                    ORDER BY content_rowid DESC;
                """), {"q": clean_q}).fetchall()
                if fts_res:
                    row_ids = [r[0] for r in fts_res]
                    return db.query(SessionRecord).filter(SessionRecord.id.in_(row_ids)).all()
            except Exception:
                pass

            # Fallback to standard LIKE
            q = f"%{clean_q}%"
            return db.query(SessionRecord).filter(
                (SessionRecord.repo_name.like(q)) |
                (SessionRecord.generated_prompt.like(q)) |
                (SessionRecord.code_symbols.like(q)) |
                (SessionRecord.source_license.like(q))
            ).order_by(SessionRecord.id.desc()).all()
        finally:
            db.close()

    def search_fts(self, query_str: str, session_id: int = None) -> List[Dict[str, Any]]:
        """Executes FTS5 full-text index query and returns structured raw source & prompt evidence snippets."""
        clean_q = query_str.strip()
        if not clean_q:
            return []

        db: SASession = self.SessionLocal()
        try:
            records = self.search_sessions(clean_q)
            results = []
            for r in records:
                if session_id and r.id != session_id:
                    continue

                symbols_text = r.code_symbols or ""
                matched_symbols = []
                if symbols_text:
                    for s in symbols_text.splitlines():
                        if clean_q.lower() in s.lower():
                            matched_symbols.append(s.strip())
                if not matched_symbols and symbols_text:
                    matched_symbols = [s.strip() for s in symbols_text.splitlines()[:3]]

                snippet = r.generated_prompt or ""
                idx = snippet.lower().find(clean_q.lower())
                if idx >= 0:
                    start = max(0, idx - 100)
                    end = min(len(snippet), idx + 300)
                    excerpt = "..." + snippet[start:end] + "..."
                else:
                    excerpt = snippet[:400]

                results.append({
                    "id": r.id,
                    "repo_name": r.repo_name,
                    "repo_url": r.repo_url,
                    "source_license": r.source_license,
                    "code_symbols": symbols_text,
                    "raw_symbol_matches": matched_symbols,
                    "prompt_snippet": excerpt,
                })
            return results
        except Exception:
            return []
        finally:
            db.close()

    def get_recent_sessions_summary(self) -> List[Dict[str, Any]]:
        """Returns lightweight session list for KB Chat selection."""
        db: SASession = self.SessionLocal()
        try:
            records = db.query(SessionRecord).order_by(SessionRecord.id.desc()).limit(20).all()
            return [{
                "id": r.id,
                "repo_name": r.repo_name,
                "repo_url": r.repo_url,
                "language": r.language,
                "source_license": r.source_license,
                "file_count": r.file_count,
                "generated_prompt": r.generated_prompt[:400] if r.generated_prompt else "",
                "commit_sha": r.commit_sha or "",
                "branch": r.branch or "",
                "secret_warnings": r.secret_warnings or 0,
                "version_number": r.version_number or 1,
            } for r in records]
        finally:
            db.close()

    def get_session_by_id(self, session_id: int) -> Optional["SessionRecord"]:
        db: SASession = self.SessionLocal()
        try:
            return db.query(SessionRecord).filter(SessionRecord.id == session_id).first()
        finally:
            db.close()

    def get_sessions_by_repo_url(self, repo_url: str) -> List["SessionRecord"]:
        """Returns all analysis sessions for a given repository URL (§51 history)."""
        db: SASession = self.SessionLocal()
        try:
            return db.query(SessionRecord).filter(
                SessionRecord.repo_url == repo_url
            ).order_by(SessionRecord.id.desc()).all()
        finally:
            db.close()

    def delete_session(self, session_id: int) -> bool:
        db: SASession = self.SessionLocal()
        try:
            record = db.query(SessionRecord).filter(SessionRecord.id == session_id).first()
            if record:
                db.delete(record)
                db.commit()
                # Remove from FTS index
                try:
                    db.execute(text("DELETE FROM session_records_fts WHERE content_rowid = :id;"), {"id": session_id})
                    db.commit()
                except Exception:
                    pass
                return True
            return False
        finally:
            db.close()

    def clear_all_sessions(self) -> bool:
        db: SASession = self.SessionLocal()
        try:
            db.query(SessionRecord).delete()
            db.commit()
            try:
                db.execute(text("DELETE FROM session_records_fts;"))
                db.commit()
            except Exception:
                pass
            return True
        finally:
            db.close()

    # ── §64 Spending Log ─────────────────────────────────────────────────────

    def log_token_usage(self, tokens: int, estimated_cost_usd: float = 0.0,
                        provider: str = "", model_id: str = "") -> bool:
        """Records token usage for the current day."""
        db: SASession = self.SessionLocal()
        try:
            date_str = datetime.datetime.now().strftime("%Y-%m-%d")
            existing = db.query(SpendingLog).filter(SpendingLog.date_str == date_str).first()
            if existing:
                existing.tokens_used += tokens
                existing.estimated_cost_usd += estimated_cost_usd
            else:
                db.add(SpendingLog(
                    date_str=date_str,
                    tokens_used=tokens,
                    estimated_cost_usd=estimated_cost_usd,
                    provider=provider,
                    model_id=model_id,
                ))
            db.commit()
            return True
        except Exception:
            return False
        finally:
            db.close()

    def get_spending_summary(self) -> Dict[str, Any]:
        """Returns spending totals for today, this month, and all time."""
        db: SASession = self.SessionLocal()
        try:
            today = datetime.datetime.now().strftime("%Y-%m-%d")
            month_prefix = datetime.datetime.now().strftime("%Y-%m")

            all_rows = db.query(SpendingLog).all()
            today_rows = [r for r in all_rows if r.date_str == today]
            month_rows = [r for r in all_rows if r.date_str.startswith(month_prefix)]

            return {
                "today_tokens": sum(r.tokens_used for r in today_rows),
                "today_cost_usd": round(sum(r.estimated_cost_usd for r in today_rows), 4),
                "month_tokens": sum(r.tokens_used for r in month_rows),
                "month_cost_usd": round(sum(r.estimated_cost_usd for r in month_rows), 4),
                "total_tokens": sum(r.tokens_used for r in all_rows),
                "total_cost_usd": round(sum(r.estimated_cost_usd for r in all_rows), 4),
                "days_tracked": len({r.date_str for r in all_rows}),
            }
        except Exception:
            return {
                "today_tokens": 0, "today_cost_usd": 0,
                "month_tokens": 0, "month_cost_usd": 0,
                "total_tokens": 0, "total_cost_usd": 0,
                "days_tracked": 0,
            }
        finally:
            db.close()

    def get_health_stats(self) -> Dict[str, Any]:
        """Returns DB statistics for the Health Center (§67)."""
        db: SASession = self.SessionLocal()
        try:
            session_count = db.query(SessionRecord).count()
            complete_count = db.query(SessionRecord).filter(
                SessionRecord.status == "complete"
            ).count()
            return {
                "session_count": session_count,
                "complete_count": complete_count,
                "db_path": self.db_path,
            }
        except Exception:
            return {"session_count": 0, "complete_count": 0, "db_path": self.db_path}
        finally:
            db.close()

    def export_all_sessions_json(self) -> Dict[str, Any]:
        """Exports all sessions as a JSON-serializable dict for backup (§65)."""
        from app.services.secrets import SecretsManager
        sessions = [r.to_dict() for r in self.get_all_sessions()]
        config = SecretsManager.load_config()
        # Remove sensitive keys from backup
        config.pop("api_key", None)
        return {"sessions": sessions, "settings": config, "export_version": "1.1"}

    def import_sessions_from_json(self, data: Dict[str, Any]) -> int:
        """Imports sessions from a backup JSON dict. Returns count imported."""
        sessions = data.get("sessions", [])
        count = 0
        db: SASession = self.SessionLocal()
        try:
            for s in sessions:
                # Check if session already exists by repo_url + created_at
                existing = db.query(SessionRecord).filter(
                    SessionRecord.repo_url == s.get("repo_url", ""),
                    SessionRecord.created_at == s.get("created_at", ""),
                ).first()
                if existing:
                    continue
                record = SessionRecord(
                    repo_url=s.get("repo_url", ""),
                    repo_name=s.get("repo_name", ""),
                    language=s.get("language", "Unknown"),
                    file_count=s.get("file_count", 0),
                    generated_prompt=s.get("generated_prompt", ""),
                    model_used=s.get("model_used", "gpt-4o"),
                    source_license=s.get("source_license", "none"),
                    status=s.get("status", "complete"),
                    commit_sha=s.get("commit_sha", ""),
                    branch=s.get("branch", ""),
                    secret_warnings=s.get("secret_warnings", 0),
                    version_number=s.get("version_number", 1),
                )
                db.add(record)
                count += 1
            db.commit()
        except Exception:
            pass
        finally:
            db.close()
        return count
