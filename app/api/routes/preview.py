import io
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from app.config import settings
from app.services.pdf_service import PDFService

router = APIRouter(prefix="/api")
pdf_service = PDFService()

@router.get("/preview/{job_id}/{page}")
async def preview_page(job_id: str, page: int):
    pdf_path = settings.UPLOADS_DIR / f"{job_id}.pdf"
    if not pdf_path.exists():
        return {"error": "PDF not found"}
    
    try:
        webp_bytes = pdf_service.render_page_preview_webp(str(pdf_path), page)
        return StreamingResponse(io.BytesIO(webp_bytes), media_type="image/webp")
    except IndexError:
        return {"error": "Page out of range"}
    except Exception as e:
        return {"error": str(e)}

@router.get("/pdf_info/{job_id}")
async def pdf_info(job_id: str):
    pdf_path = settings.UPLOADS_DIR / f"{job_id}.pdf"
    if not pdf_path.exists():
        return {"error": "PDF not found"}
    return pdf_service.get_info(str(pdf_path))
