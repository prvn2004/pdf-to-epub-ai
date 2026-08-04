import uuid
import threading
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Form
from app.config import settings
from app.services.session_service import session_manager
from app.services.pipeline_service import PipelineService

router = APIRouter(prefix="/api")
pipeline = PipelineService()

@router.post("/upload")
async def upload_pdf(
    file: UploadFile = File(...),
    title: str = Form(""),
    author: str = Form("")
):
    job_id = uuid.uuid4().hex[:12]
    pdf_path = settings.UPLOADS_DIR / f"{job_id}.pdf"
    content = await file.read()
    pdf_path.write_bytes(content)

    session_manager.create_session(job_id)

    metadata = {
        "filename": file.filename,
        "title": title or Path(file.filename).stem.replace("_", " ").title(),
        "author": author or "Unknown",
    }

    thread = threading.Thread(
        target=pipeline.process_pdf,
        args=(job_id, str(pdf_path), metadata)
    )
    thread.start()
    return {"job_id": job_id, "status": "started"}
