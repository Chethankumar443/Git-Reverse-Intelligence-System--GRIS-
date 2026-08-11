"""
Git Reverse — FastAPI Main Router
Mounts all API sub-routers under the GRIS application.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

from app.api.analysis import router as analysis_router
from app.api.sessions import router as sessions_router
from app.api.chat import router as chat_router
from app.api.config import router as config_router
from app.api.health import router as health_router
from app.api.export import router as export_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="Git Reverse Intelligence System",
        description="Repository intelligence engine — BYOK AI reverse engineering platform",
        version="1.1.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
    )

    # CORS — allow local browser origin
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:4321", "http://localhost:8000", "http://127.0.0.1:8000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount API routers
    app.include_router(analysis_router)
    app.include_router(sessions_router)
    app.include_router(chat_router)
    app.include_router(config_router)
    app.include_router(health_router)
    app.include_router(export_router)

    # Serve built Astro frontend as static files
    root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    frontend_dist = os.path.join(root_dir, "frontend", "dist")
    if os.path.isdir(frontend_dist):
        app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")
    else:
        @app.get("/")
        async def root():
            return {
                "app": "Git Reverse Intelligence System",
                "version": "1.1.0",
                "status": "API only — run 'npm run build' in frontend/ to serve the UI",
                "api_docs": "/api/docs",
            }

    return app
