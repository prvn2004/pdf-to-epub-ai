from abc import ABC, abstractmethod
from typing import Dict, Any, Tuple
from app.models.ocr import OCRResult

class BaseVisionLLMClient(ABC):
    @abstractmethod
    def ocr_page(self, image_b64: str, page_size: Tuple[int, int], attempts: int = 3) -> OCRResult:
        """Process page image and return OCR result with markdown and image bounding boxes."""
        pass

class BasePDFRenderer(ABC):
    @abstractmethod
    def get_info(self, pdf_path: str) -> Dict[str, Any]:
        """Extract metadata and page count from PDF."""
        pass

    @abstractmethod
    def render_page_pixmap(self, pdf_path: str, pageno_idx: int, dpi: int = 200) -> Any:
        """Render specific page to PyMuPDF Pixmap or byte array."""
        pass
