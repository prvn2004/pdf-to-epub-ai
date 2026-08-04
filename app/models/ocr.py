from typing import List, Optional
from pydantic import BaseModel, Field

class ImageBox(BaseModel):
    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0
    caption: Optional[str] = ""

class CropItem(BaseModel):
    path: str
    rel_path: str
    caption: str = ""
    x: int
    y: int
    width: int
    height: int
    px_width: int
    px_height: int

class OCRResult(BaseModel):
    markdown: str = ""
    images: List[ImageBox] = Field(default_factory=list)
