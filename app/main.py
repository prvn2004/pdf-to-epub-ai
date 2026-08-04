from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.config import settings

from app.api.routes.pages import router as pages_router
from app.api.routes.upload import router as upload_router
from app.api.routes.stream import router as stream_router
from app.api.routes.preview import router as preview_router
from app.api.routes.assets import router as assets_router
from app.api.routes.session import router as session_router

app = FastAPI(title="Folio — PDF to Markdown & EPUB")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

# Mount static directory if it exists
if settings.STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=settings.STATIC_DIR), name="static")

# Register routers
app.include_router(pages_router)
app.include_router(upload_router)
app.include_router(stream_router)
app.include_router(preview_router)
app.include_router(assets_router)
app.include_router(session_router)
