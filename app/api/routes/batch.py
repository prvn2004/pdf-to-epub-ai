from typing import List
from fastapi import APIRouter, Request, Response, UploadFile, File, Form, BackgroundTasks, HTTPException
from app.config import settings
from app.core.security import security_service
from app.services.session_service import session_manager
from app.services.pipeline_service import PipelineService

router = APIRouter()

@router.post("/api/batch/upload")
async def batch_upload(
    request: Request,
    response: Response,
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    title: str = Form(""),
    author: str = Form("")
):
    """
    Accept multiple PDF file uploads simultaneously.
    Validates each file and initializes background conversion pipelines.
    """
    client_id = security_service.get_or_create_client_token(request, response)
    created_jobs = []

    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    pipeline_service = PipelineService()

    for idx, file in enumerate(files):
        content = await security_service.validate_pdf_upload(file)
        job_id = security_service.generate_secure_job_token()

        pdf_path = settings.UPLOADS_DIR / f"{job_id}.pdf"
        pdf_path.write_bytes(content)

        doc_title = title if len(files) == 1 and title else (file.filename or f"Document {idx+1}")
        doc_author = author if author else "Unknown"

        session_manager.create_session(job_id, client_id=client_id, title=doc_title, author=doc_author)
        
        meta = {"title": doc_title, "author": doc_author}
        background_tasks.add_task(pipeline_service.process_pdf, job_id, str(pdf_path), meta)

        created_jobs.append({
            "job_id": job_id,
            "filename": file.filename,
            "title": doc_title,
            "author": doc_author,
            "status": "processing"
        })

    return {
        "status": "ok",
        "client_id": client_id,
        "count": len(created_jobs),
        "jobs": created_jobs
    }

@router.get("/api/jobs")
async def list_jobs(request: Request, response: Response):
    """List all jobs belonging to the current client session."""
    client_id = security_service.get_or_create_client_token(request, response)
    jobs = session_manager.get_client_sessions(client_id)
    return {"status": "ok", "client_id": client_id, "jobs": jobs}

@router.post("/api/pause/{job_id}")
async def pause_job(request: Request, response: Response, job_id: str):
    """Pause an actively running conversion job."""
    client_token = security_service.get_or_create_client_token(request, response)
    if not session_manager.verify_job_owner(job_id, client_token):
        raise HTTPException(status_code=403, detail="Unauthorized access to job control")

    success = session_manager.pause_session(job_id)
    if not success:
        raise HTTPException(status_code=404, detail="Job not found or already completed")
    return {"status": "ok", "job_id": job_id, "state": "paused"}

@router.post("/api/resume/{job_id}")
async def resume_job(request: Request, response: Response, job_id: str, background_tasks: BackgroundTasks):
    """Resume a paused or incomplete conversion job."""
    client_token = security_service.get_or_create_client_token(request, response)
    if not session_manager.verify_job_owner(job_id, client_token):
        raise HTTPException(status_code=403, detail="Unauthorized access to job control")

    sess = session_manager.get_session(job_id)
    if not sess:
        raise HTTPException(status_code=404, detail="Job not found")

    pdf_path = settings.UPLOADS_DIR / f"{job_id}.pdf"
    if not pdf_path.exists():
        raise HTTPException(
            status_code=400,
            detail="Source PDF upload is no longer available on server. Please upload again."
        )

    session_manager.update_session(job_id, status="processing", is_paused=False, error=None)
    session_manager.emit_event(job_id, "progress", {
        "phase": "resuming",
        "msg": "▶️ Resuming conversion pipeline..."
    })

    pipeline_service = PipelineService()
    meta = sess.get("telemetry", {})
    background_tasks.add_task(pipeline_service.process_pdf, job_id, str(pdf_path), meta)

    return {"status": "ok", "job_id": job_id, "state": "resuming"}

@router.delete("/api/job/{job_id}")
async def delete_job(request: Request, response: Response, job_id: str):
    """Cancel job and purge session files from disk."""
    client_token = security_service.get_or_create_client_token(request, response)
    if not session_manager.verify_job_owner(job_id, client_token):
        raise HTTPException(status_code=403, detail="Unauthorized access to delete job")

    success = session_manager.delete_session(job_id)
    return {"status": "ok", "job_id": job_id, "deleted": success}
