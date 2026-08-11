"""
Git Reverse — Sessions API Router
GET    /api/sessions         → list all sessions (most recent first)
GET    /api/sessions/{id}    → get one session
DELETE /api/sessions/{id}    → delete one session
GET    /api/sessions/{id}/prompt → get full prompt text
"""
from fastapi import APIRouter, HTTPException
from app.services.database import DatabaseManager

router = APIRouter()


@router.get("/api/sessions")
async def list_sessions(q: str = ""):
    """Returns all sessions (optionally filtered by search query)."""
    import asyncio
    db = DatabaseManager()
    if q.strip():
        records = await asyncio.to_thread(db.search_sessions, q)
    else:
        records = await asyncio.to_thread(db.get_all_sessions)
    return [r.to_dict() for r in records]


@router.get("/api/sessions/{session_id}")
async def get_session(session_id: int):
    import asyncio
    db = DatabaseManager()
    rec = await asyncio.to_thread(db.get_session_by_id, session_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Session not found")
    return rec.to_dict()


@router.get("/api/sessions/{session_id}/prompt")
async def get_session_prompt(session_id: int):
    import asyncio
    db = DatabaseManager()
    rec = await asyncio.to_thread(db.get_session_by_id, session_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Session not found")
    return {
        "session_id": rec.id,
        "repo_name": rec.repo_name,
        "repo_url": rec.repo_url,
        "source_license": rec.source_license,
        "prompt": rec.generated_prompt,
        "status": rec.status,
    }


@router.delete("/api/sessions/{session_id}")
async def delete_session(session_id: int):
    import asyncio
    db = DatabaseManager()
    ok = await asyncio.to_thread(db.delete_session, session_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"deleted": True, "session_id": session_id}


@router.delete("/api/sessions")
async def clear_sessions():
    import asyncio
    db = DatabaseManager()
    await asyncio.to_thread(db.clear_all_sessions)
    return {"cleared": True}
