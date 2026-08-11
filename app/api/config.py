"""
Git Reverse — Config/Settings API Router
GET  /api/config         → current settings (API key presence only, never value)
POST /api/config         → save settings + API key to OS keyring
POST /api/config/test    → test LLM connectivity
GET  /api/config/models  → fetch available models from provider
"""
import asyncio
import logging
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

from app.services.secrets import SecretsManager
from app.services.llm_client import LLMClient, fetch_provider_models, detect_provider_from_key

logger = logging.getLogger("gris.api.config")
router = APIRouter()


class SaveConfigRequest(BaseModel):
    provider_preset: Optional[str] = None
    base_url: Optional[str] = None
    model_id: Optional[str] = None
    api_key: Optional[str] = None
    github_token: Optional[str] = None
    theme: Optional[str] = None
    export_dir: Optional[str] = None
    daily_spend_limit_usd: Optional[float] = None
    monthly_spend_limit_usd: Optional[float] = None
    spend_limit_action: Optional[str] = None


class TestConnectionRequest(BaseModel):
    api_key: Optional[str] = None
    base_url: Optional[str] = "https://api.openai.com/v1"
    model_id: Optional[str] = "gpt-4o"


@router.get("/api/config")
async def get_config():
    config = await asyncio.to_thread(SecretsManager.load_config)
    api_key = await asyncio.to_thread(SecretsManager.get_api_key)
    github_token = await asyncio.to_thread(SecretsManager.get_github_token)
    # Never expose actual key values — only presence
    config["has_api_key"] = bool(api_key)
    config["has_github_token"] = bool(github_token)
    config.pop("api_key", None)
    config.pop("github_token", None)
    return config


@router.post("/api/config")
async def save_config(body: SaveConfigRequest):
    config = await asyncio.to_thread(SecretsManager.load_config)
    updates = body.model_dump(exclude_none=True)

    # Handle secrets separately
    if "api_key" in updates:
        await asyncio.to_thread(SecretsManager.set_api_key, updates.pop("api_key"))
    if "github_token" in updates:
        await asyncio.to_thread(SecretsManager.set_github_token, updates.pop("github_token"))

    config.update(updates)
    ok = await asyncio.to_thread(SecretsManager.save_config, config)
    return {"saved": ok}


@router.post("/api/config/test")
async def test_connection(body: TestConnectionRequest):
    api_key = body.api_key
    if not api_key:
        api_key = await asyncio.to_thread(SecretsManager.get_api_key)

    if not api_key:
        return {"ok": False, "message": "No API key configured."}

    llm = LLMClient(
        api_key=api_key,
        base_url=body.base_url or "https://api.openai.com/v1",
        model_id=body.model_id or "gpt-4o",
    )
    ok, msg = await asyncio.to_thread(llm.test_connection)
    return {"ok": ok, "message": msg}


@router.get("/api/config/models")
async def list_models():
    api_key = await asyncio.to_thread(SecretsManager.get_api_key)
    config = await asyncio.to_thread(SecretsManager.load_config)
    base_url = config.get("base_url", "https://api.openai.com/v1")
    provider = config.get("provider_preset", "")

    if not api_key:
        return {"models": []}

    models = await asyncio.to_thread(
        fetch_provider_models, api_key, base_url, provider
    )
    return {"models": models}
