from fastapi import APIRouter
from fastapi.responses import FileResponse
from app.config import settings
from app.services.session_service import session_manager

router = APIRouter()

@router.get("/download/{job_id}")
async def download_markdown(job_id: str):
    out_dir = settings.OUTPUTS_DIR / job_id
    mds = list(out_dir.glob("*.md")) if out_dir.exists() else []
    if not mds:
        return {"error": "Markdown not found"}
    return FileResponse(mds[0], media_type="text/markdown", filename=mds[0].name)

@router.get("/crops/{job_id}/{filename}")
async def serve_crop(job_id: str, filename: str):
    # Ensure no path traversal
    crop_dir = (settings.CROPS_DIR / job_id).resolve()
    fpath = (crop_dir / filename).resolve()
    
    if not fpath.is_relative_to(settings.CROPS_DIR) or not fpath.exists():
        return {"error": "Crop not found"}
    return FileResponse(fpath, media_type="image/jpeg")

@router.get("/api/telemetry/{job_id}")
async def get_telemetry(job_id: str):
    sess = session_manager.get_session(job_id)
    if not sess:
        return {"error": "Job not found"}
    return sess.get("telemetry", {})
