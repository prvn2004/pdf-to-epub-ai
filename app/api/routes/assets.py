from pathlib import Path
from fastapi import APIRouter, Query
from fastapi.responses import FileResponse, Response
from app.config import settings
from app.services.session_service import session_manager
from app.services.epub_service import EPUBService
from app.services.cleanup_service import cleanup_service

router = APIRouter()
epub_service = EPUBService()

@router.get("/download/{job_id}")
async def download_file(
    job_id: str,
    format: str = Query("md", pattern="^(md|epub)$")
):
    # Trigger background 10-minute PDF retention cleanup
    cleanup_service.cleanup_expired_pdf_uploads()

    sess = session_manager.get_session(job_id)
    if not sess:
        return {"error": "Job session not found"}

    valid_pages = session_manager.get_valid_cached_pages(job_id)
    if not valid_pages:
        return {"error": "No completed pages available for download yet"}

    is_done = sess.get("status") == "done"
    out_dir = settings.OUTPUTS_DIR / job_id
    out_dir.mkdir(parents=True, exist_ok=True)

    if format == "epub":
        try:
            epub_path = epub_service.generate_epub(job_id, partial=not is_done)
            return FileResponse(
                epub_path,
                media_type="application/epub+zip",
                filename=epub_path.name
            )
        except Exception as e:
            return {"error": f"Failed to generate EPUB: {str(e)}"}

    # Format == "md"
    mds = list(out_dir.glob("*.md")) if is_done else []
    if mds and is_done:
        return FileResponse(mds[0], media_type="text/markdown", filename=mds[0].name)

    # Partial Markdown download
    sorted_pagenos = sorted(valid_pages.keys())
    md_parts = []
    for pageno in sorted_pagenos:
        p_data = valid_pages[pageno]
        md_parts.append(f"## Page {pageno}\n\n{p_data.get('text', '').strip()}")

    title = sess.get("telemetry", {}).get("title") or "Book"
    content = f"# {title} (Partial)\n\n" + "\n\n".join(md_parts) + "\n"
    
    return Response(
        content=content.encode("utf-8"),
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="{job_id}_partial.md"'}
    )

@router.get("/crops/{job_id}/{filename}")
async def serve_crop(job_id: str, filename: str):
    crop_dir = (settings.CROPS_DIR / job_id).resolve()
    fpath = (crop_dir / filename).resolve()
    
    if not fpath.is_relative_to(settings.CROPS_DIR) or not fpath.exists():
        return {"error": "Crop not found"}
    return FileResponse(
        fpath,
        media_type="image/jpeg",
        headers={"Cache-Control": "public, max-age=31536000, immutable"}
    )

@router.get("/api/telemetry/{job_id}")
async def get_telemetry(job_id: str):
    sess = session_manager.get_session(job_id)
    if not sess:
        return {"error": "Job not found"}
    return sess.get("telemetry", {})
