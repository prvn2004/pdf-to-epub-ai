from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class PageTimeMetric(BaseModel):
    page: int
    sec: float
    render_sec: float
    images: int

class Telemetry(BaseModel):
    phases: List[Dict[str, Any]] = Field(default_factory=list)
    page_times: List[PageTimeMetric] = Field(default_factory=list)
    image_count: int = 0
    total_sec: float = 0.0

class PageResult(BaseModel):
    pageno: int
    text: str
    crops: int = 0
    images: int = 0
    render_sec: float = 0.0
    time_sec: float = 0.0

class JobSession(BaseModel):
    job_id: str
    status: str = "processing"  # processing, done, error
    pages_total: int = 0
    pages_done: int = 0
    telemetry: Telemetry = Field(default_factory=Telemetry)
    md_path: Optional[str] = None
    error: Optional[str] = None
