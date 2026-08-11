"""
Git Reverse — Health API Router
GET /api/health → system diagnostics
"""
import asyncio
import os
import shutil
from fastapi import APIRouter
from app.services.database import DatabaseManager

router = APIRouter()


@router.get("/api/health")
async def health():
    db = DatabaseManager()
    db_stats = await asyncio.to_thread(db.get_health_stats)
    spending = await asyncio.to_thread(db.get_spending_summary)

    # Disk free for AppData drive
    try:
        appdata = os.getenv("APPDATA") or os.path.expanduser("~")
        total, used, free = shutil.disk_usage(appdata)
        disk_free_gb = round(free / (1024**3), 2)
    except Exception:
        disk_free_gb = -1

    # Check DB file size
    db_size_kb = 0
    try:
        db_size_kb = round(os.path.getsize(db_stats.get("db_path", "")) / 1024, 1)
    except Exception:
        pass

    return {
        "status": "ok",
        "session_count": db_stats.get("session_count", 0),
        "complete_count": db_stats.get("complete_count", 0),
        "db_path": db_stats.get("db_path", ""),
        "db_size_kb": db_size_kb,
        "disk_free_gb": disk_free_gb,
        "spending": spending,
    }
