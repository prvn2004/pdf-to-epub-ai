import threading
from fastapi import APIRouter
from app.config import settings
from app.services.session_service import session_manager
from app.services.pipeline_service import PipelineService

router = APIRouter(prefix="/api")
pipeline = PipelineService()

@router.get("/session/{job_id}")
async def get_session_info(job_id: str):
    sess = session_manager.get_session(job_id)
    if not sess:
        return {"error": "Session not found"}
    
    valid_pages = session_manager.get_valid_cached_pages(job_id)
    total = sess.get("pages_total", 0)
    missing = [p for p in range(1, total + 1) if p not in valid_pages] if total > 0 else []

    return {
        "job_id": sess.get("job_id"),
        "status": sess.get("status"),
        "pages_total": total,
        "pages_done": len(valid_pages),
        "missing_pages": missing,
        "completed_pages": valid_pages,
        "telemetry": sess.get("telemetry", {}),
        "error": sess.get("error"),
    }

@router.post("/resume/{job_id}")
async def resume_session(job_id: str):
    sess = session_manager.get_session(job_id)
    if not sess:
        return {"error": "Session not found"}

    pdf_path = settings.UPLOADS_DIR / f"{job_id}.pdf"
    if not pdf_path.exists():
        return {"error": "Original PDF file not found to resume"}

    current_status = sess.get("status")
    valid_pages = session_manager.get_valid_cached_pages(job_id)
    total = sess.get("pages_total", 0)
    missing = [p for p in range(1, total + 1) if p not in valid_pages] if total > 0 else []

    if current_status == "processing" and not missing:
        return {"job_id": job_id, "status": "already_processing"}

    if current_status == "done" and not missing:
        return {"job_id": job_id, "status": "already_completed"}

    session_manager.update_session(job_id, status="processing")
    metadata = {
        "title": "Resumed Book",
        "author": "Unknown",
    }

    thread = threading.Thread(
        target=pipeline.process_pdf,
        args=(job_id, str(pdf_path), metadata)
    )
    thread.start()
    return {"job_id": job_id, "status": "resumed", "missing_pages": len(missing)}
