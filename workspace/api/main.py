"""
Git Reverse Workspace API
Self-hosted collaborative workspace where humans and AI agents co-exist.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from database.db import init_db
from auth.router import router as auth_router
from agents.router import router as agents_router
from channels.router import router as channels_router
from audit.router import router as audit_router
from ws.router import router as ws_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: initialize database tables."""
    await init_db()
    yield


app = FastAPI(
    title="Git Reverse Workspace API",
    description="Self-hosted workspace for humans and AI agents to collaborate on repository intelligence.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow the Vite dev server and production Nginx
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://workspace-web:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(agents_router, prefix="/api/agents", tags=["agents"])
app.include_router(channels_router, prefix="/api/channels", tags=["channels"])
app.include_router(audit_router, prefix="/api/audit", tags=["audit"])
app.include_router(ws_router, prefix="/ws", tags=["websocket"])


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "git-reverse-workspace-api"}
