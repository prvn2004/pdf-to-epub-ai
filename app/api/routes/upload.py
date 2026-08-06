import threading
from pathlib import Path
from fastapi import APIRouter, Request, Response, UploadFile, File, Form
from app.config import settings
from app.core.security import security_service
from app.services.session_service import session_manager
from app.services.pipeline_service import PipelineService

router = APIRouter(prefix="/api")
pipeline = PipelineService()

@router.post("/upload")
async def upload_pdf(
    request: Request,
    response: Response,
    file: UploadFile = File(...),
    title: str = Form(""),
    author: str = Form("")
):
    client_token = security_service.get_or_create_client_token(request, response)
    content = await security_service.validate_pdf_upload(file)

    # 24-character unguessable secret job token
    job_id = security_service.generate_secure_job_token()
    pdf_path = settings.UPLOADS_DIR / f"{job_id}.pdf"
    pdf_path.write_bytes(content)

    doc_title = title or Path(file.filename).stem.replace("_", " ").title()
    doc_author = author or "Unknown"

    session_manager.create_session(job_id, client_id=client_token, title=doc_title, author=doc_author)

    metadata = {
        "filename": file.filename,
        "title": doc_title,
        "author": doc_author,
    }

    thread = threading.Thread(
        target=pipeline.process_pdf,
        args=(job_id, str(pdf_path), metadata)
    )
    thread.start()
    return {"job_id": job_id, "status": "started"}
