from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from app.config import settings

router = APIRouter()

@router.get("/", response_class=HTMLResponse)
async def get_index():
    index_file = settings.TEMPLATES_DIR / "index.html"
    return HTMLResponse(content=index_file.read_text(encoding="utf-8"))
