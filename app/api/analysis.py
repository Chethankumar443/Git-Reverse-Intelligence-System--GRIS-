"""
Git Reverse — Analysis API Router
POST /api/analysis/start   → start analysis job (returns session_id immediately)
WS   /ws/analysis/{id}     → WebSocket stream for live progress + LLM tokens
"""
import asyncio
import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel

from app.core.analysis_runner import run_analysis

logger = logging.getLogger("gris.api.analysis")

router = APIRouter()

# In-memory job registry: session_id → accumulated prompt once done
_jobs: dict[str, dict] = {}


class StartRequest(BaseModel):
    url: str
    depth: str = "recreation"
    prompt_type: str = "Clone Prompt"


class StartResponse(BaseModel):
    job_id: str
    status: str = "started"


@router.post("/api/analysis/start", response_model=StartResponse)
async def start_analysis(body: StartRequest):
    """Kick off a background analysis job. Returns a job_id to subscribe via WS."""
    import uuid
    job_id = str(uuid.uuid4())
    _jobs[job_id] = {"status": "running", "session_id": None, "prompt": ""}

    async def _run():
        async for event in run_analysis(body.url, body.prompt_type):
            _jobs[job_id]["last_event"] = event
            if event["type"] == "done":
                _jobs[job_id]["status"] = "done"
                _jobs[job_id]["session_id"] = event.get("session_id")
                _jobs[job_id]["prompt"] = event.get("prompt", "")
            elif event["type"] == "error":
                _jobs[job_id]["status"] = "error"
                _jobs[job_id]["error"] = event.get("msg")

    asyncio.create_task(_run())
    return StartResponse(job_id=job_id)


@router.get("/api/analysis/{job_id}")
async def get_job_status(job_id: str):
    """Poll job status (for non-WS clients)."""
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.websocket("/ws/analysis/{job_id}")
async def ws_analysis(websocket: WebSocket, job_id: str):
    """
    WebSocket endpoint that streams all analysis events in real time.
    The client should call POST /api/analysis/start first, then open this socket.
    Events are JSON: {"type": ..., ...}
    """
    await websocket.accept()
    try:
        # Stream fresh if job exists but isn't done yet, or re-run
        url = _jobs.get(job_id, {}).get("url", "")
        prompt_type = _jobs.get(job_id, {}).get("prompt_type", "Clone Prompt")

        # Allow passing url in query params for direct WS connect
        if not url:
            url = websocket.query_params.get("url", "")
            prompt_type = websocket.query_params.get("prompt_type", "Clone Prompt")

        if not url:
            await websocket.send_json({"type": "error", "msg": "No repository URL provided."})
            await websocket.close()
            return

        async for event in run_analysis(url, prompt_type):
            try:
                await websocket.send_json(event)
            except WebSocketDisconnect:
                logger.info(f"WS client disconnected from job {job_id}")
                return

    except WebSocketDisconnect:
        logger.info(f"WS disconnected: {job_id}")
    except Exception as e:
        logger.error(f"WS error: {e}")
        try:
            await websocket.send_json({"type": "error", "msg": str(e)})
        except Exception:
            pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass
