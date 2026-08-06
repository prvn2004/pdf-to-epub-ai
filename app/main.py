from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from app.config import settings
from app.services.ttl_service import ttl_service

from app.api.routes.pages import router as pages_router
from app.api.routes.upload import router as upload_router
from app.api.routes.batch import router as batch_router
from app.api.routes.stream import router as stream_router
from app.api.routes.preview import router as preview_router
from app.api.routes.assets import router as assets_router
from app.api.routes.session import router as session_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start background TTL storage reclamation daemon on startup
    ttl_service.start_background_cleanup()
    yield

app = FastAPI(title="Folio — PDF to Markdown & EPUB", lifespan=lifespan)

# GZip compression middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)

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
app.include_router(batch_router)
app.include_router(stream_router)
app.include_router(preview_router)
app.include_router(assets_router)
app.include_router(session_router)
