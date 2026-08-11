"""
Git Reverse — Export API Router
POST /api/export → generate PDF/Markdown export and return file download
"""
import asyncio
import os
import tempfile
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional

from app.services.exporter import export_pdf_file, export_markdown_file
from app.services.database import DatabaseManager

router = APIRouter()


class ExportRequest(BaseModel):
    session_id: int
    format: str = "pdf"  # "pdf" | "markdown"


@router.post("/api/export")
async def export_session(body: ExportRequest):
    db = DatabaseManager()
    rec = await asyncio.to_thread(db.get_session_by_id, body.session_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Session not found")

    ext = "pdf" if body.format == "pdf" else "md"
    safe_name = rec.repo_name.replace("/", "_").replace(" ", "_")
    filename = f"git-reverse-{safe_name}.{ext}"

    # Write to temp file
    tmp_dir = tempfile.gettempdir()
    filepath = os.path.join(tmp_dir, filename)

    if body.format == "pdf":
        ok = await asyncio.to_thread(
            export_pdf_file,
            filepath,
            rec.repo_name,
            rec.repo_url,
            rec.source_license,
            rec.generated_prompt or "",
        )
        # WeasyPrint fallback writes .html — adjust
        if not os.path.exists(filepath) and os.path.exists(filepath + ".html"):
            filepath = filepath + ".html"
            filename = filename + ".html"
    else:
        ok = await asyncio.to_thread(
            export_markdown_file,
            filepath,
            rec.repo_name,
            rec.repo_url,
            rec.source_license,
            rec.generated_prompt or "",
        )

    if not ok or not os.path.exists(filepath):
        raise HTTPException(status_code=500, detail="Export generation failed")

    media_type = "application/pdf" if filepath.endswith(".pdf") else (
        "text/html" if filepath.endswith(".html") else "text/markdown"
    )
    return FileResponse(
        filepath,
        media_type=media_type,
        filename=filename,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
