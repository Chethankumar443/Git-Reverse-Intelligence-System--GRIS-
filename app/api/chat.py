"""
Git Reverse — Chat API Router
POST /api/chat        → streaming SSE chat response
POST /api/chat/fts    → FTS5 context search for a session
"""
import asyncio
import json
import logging
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional

from app.services.llm_client import LLMClient
from app.services.database import DatabaseManager
from app.services.secrets import SecretsManager

logger = logging.getLogger("gris.api.chat")
router = APIRouter()


class ChatTurn(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    message: str
    history: List[ChatTurn] = []
    session_id: Optional[int] = None
    ai_mode: str = "General"


class FtsRequest(BaseModel):
    query: str
    session_id: Optional[int] = None


@router.post("/api/chat")
async def chat(body: ChatRequest):
    """
    SSE streaming chat endpoint.
    Returns text/event-stream with data: {"text": "..."} events.
    Final event: data: {"done": true}
    """
    api_key = await asyncio.to_thread(SecretsManager.get_api_key)
    config = await asyncio.to_thread(SecretsManager.load_config)
    db = DatabaseManager()

    # Build system context from session KB if session_id provided
    system_context = ""
    if body.session_id:
        rec = await asyncio.to_thread(db.get_session_by_id, body.session_id)
        if rec:
            system_context = (
                f"## Active Repository Context\n"
                f"- Repository: {rec.repo_name}\n"
                f"- URL: {rec.repo_url}\n"
                f"- License: {rec.source_license}\n"
                f"- Status: {rec.status}\n\n"
                f"## Knowledge Base (Recreation Prompt)\n"
                f"{rec.generated_prompt[:6000]}\n\n"
            )
            if rec.code_symbols:
                system_context += f"## Raw AST Symbols\n{rec.code_symbols[:2000]}\n\n"

    if not api_key:
        async def no_key_gen():
            yield f"data: {json.dumps({'text': '[Notice: No LLM API Key configured. Add one in Settings.\\n'})}\n\n"
            yield f"data: {json.dumps({'done': True})}\n\n"
        return StreamingResponse(no_key_gen(), media_type="text/event-stream")

    llm = LLMClient(
        api_key=api_key,
        base_url=config.get("base_url", "https://api.openai.com/v1"),
        model_id=config.get("model_id", "gpt-4o"),
    )
    history = [{"role": t.role, "content": t.content} for t in body.history]

    async def event_gen():
        token_queue: asyncio.Queue = asyncio.Queue()
        loop = asyncio.get_event_loop()

        def stream_thread():
            try:
                for tok in llm.stream_chat(
                    system_context=system_context,
                    user_message=body.message,
                    history=history,
                    ai_mode=body.ai_mode,
                ):
                    loop.call_soon_threadsafe(token_queue.put_nowait, tok)
            finally:
                loop.call_soon_threadsafe(token_queue.put_nowait, None)

        task = loop.run_in_executor(None, stream_thread)
        while True:
            tok = await token_queue.get()
            if tok is None:
                break
            yield f"data: {json.dumps({'text': tok})}\n\n"
        await task
        yield f"data: {json.dumps({'done': True})}\n\n"

    return StreamingResponse(event_gen(), media_type="text/event-stream")


@router.post("/api/chat/fts")
async def fts_search(body: FtsRequest):
    """FTS5 full-text search across the knowledge base."""
    db = DatabaseManager()
    results = await asyncio.to_thread(db.search_fts, body.query, body.session_id)
    return {"results": results}
