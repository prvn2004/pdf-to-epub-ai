import io
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse
from app.config import settings
from app.core.security import security_service
from app.services.session_service import session_manager
from app.services.pdf_service import PDFService

router = APIRouter(prefix="/api")
pdf_service = PDFService()

@router.get("/preview/{job_id}/{page}")
async def preview_page(request: Request, job_id: str, page: int):
    client_token = security_service.get_or_create_client_token(request)
    if not session_manager.verify_job_owner(job_id, client_token):
        raise HTTPException(status_code=403, detail="Unauthorized access to page preview")

    pdf_path = settings.UPLOADS_DIR / f"{job_id}.pdf"
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail="PDF not found")
    
    # Correct 1-based page number to 0-based PyMuPDF index
    page_idx = max(0, page - 1)
    try:
        webp_bytes = pdf_service.render_page_preview_webp(str(pdf_path), page_idx)
        return StreamingResponse(io.BytesIO(webp_bytes), media_type="image/webp")
    except IndexError:
        raise HTTPException(status_code=404, detail="Page out of range")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/pdf_info/{job_id}")
async def pdf_info(request: Request, job_id: str):
    client_token = security_service.get_or_create_client_token(request)
    if not session_manager.verify_job_owner(job_id, client_token):
        raise HTTPException(status_code=403, detail="Unauthorized access to PDF info")

    pdf_path = settings.UPLOADS_DIR / f"{job_id}.pdf"
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail="PDF not found")
    return pdf_service.get_info(str(pdf_path))
