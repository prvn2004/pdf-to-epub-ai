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

    def render_page_for_ocr(self, pdf_path: str, pageno_idx: int) -> Tuple[str, Tuple[int, int], float, Any]:
        """Render page to JPEG base64 string capped by MAX_IMAGE_SIDE. Returns (image_b64, page_size, scale, pix)."""
        pix = self.renderer.render_page_pixmap(pdf_path, pageno_idx, dpi=200)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        
        scale = min(1.0, settings.MAX_IMAGE_SIDE / max(img.size))
        if scale < 1.0:
            img = img.resize((int(img.width * scale), int(img.height * scale)), Image.LANCZOS)
        
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=78)
        img_b64 = base64.b64encode(buf.getvalue()).decode()
        return img_b64, (pix.height, pix.width), scale, pix

    def render_page_preview_webp(self, pdf_path: str, pageno_idx: int) -> bytes:
        """Render page to WEBP format for quick UI preview."""
        pix = self.renderer.render_page_pixmap(pdf_path, pageno_idx, dpi=150)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        buf = io.BytesIO()
        img.save(buf, format="WEBP", quality=70)
        return buf.getvalue()
