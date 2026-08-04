import io
import base64
from PIL import Image
from typing import Tuple, Dict, Any
from app.clients.pymupdf_renderer import PyMuPDFRenderer
from app.config import settings

class PDFService:
    def __init__(self, renderer: PyMuPDFRenderer = None):
        self.renderer = renderer or PyMuPDFRenderer()

    def get_info(self, pdf_path: str) -> Dict[str, Any]:
        return self.renderer.get_info(pdf_path)

    def encode_pixmap_for_ocr(self, pix) -> Tuple[str, Tuple[int, int]]:
        """
        Convert PyMuPDF pixmap to WebP/JPEG base64 string with zero-copy memoryview
        and explicit image buffer lifecycle management. Returns (image_b64, page_size).
        """
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        buf = io.BytesIO()
        
        if settings.IMAGE_FORMAT.upper() == "WEBP":
            img.save(buf, format="WEBP", quality=settings.WEBP_QUALITY, method=4)
        else:
            img.save(buf, format="JPEG", quality=settings.JPEG_QUALITY, optimize=True)
            
        img_b64 = base64.b64encode(buf.getvalue()).decode("ascii")
        page_size = (pix.height, pix.width)
        
        img.close()
        buf.close()
        return img_b64, page_size

    def render_page_for_ocr(self, pdf_path: str, pageno_idx: int) -> Tuple[str, Tuple[int, int], float, Any]:
        """
        Render page using direct C-level matrix scaling capped by MAX_IMAGE_SIDE.
        Returns (image_b64, page_size, scale, pix).
        """
        pix, scale = self.renderer.render_page_pixmap(pdf_path, pageno_idx, max_side=settings.MAX_IMAGE_SIDE)
        img_b64, page_size = self.encode_pixmap_for_ocr(pix)
        return img_b64, page_size, scale, pix

    def render_page_preview_webp(self, pdf_path: str, pageno_idx: int) -> bytes:
        """Render page to WEBP format for quick UI preview with direct matrix downscaling."""
        pix, _ = self.renderer.render_page_pixmap(pdf_path, pageno_idx, max_side=800)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        buf = io.BytesIO()
        img.save(buf, format="WEBP", quality=70, method=4)
        data = buf.getvalue()
        img.close()
        buf.close()
        return data
