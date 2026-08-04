import fitz
from typing import Dict, Any, Tuple
from app.clients.base import BasePDFRenderer

class PyMuPDFRenderer(BasePDFRenderer):
    def get_info(self, pdf_path: str) -> Dict[str, Any]:
        doc = fitz.open(pdf_path)
        info = {"pages": len(doc), "metadata": doc.metadata}
        doc.close()
        return info

    def render_page_pixmap(self, pdf_path: str, pageno_idx: int, max_side: int = 1280) -> Tuple[Any, float]:
        """
        Directly render PDF page to PyMuPDF pixmap scaled to fit within max_side.
        Bypasses high-DPI full-resolution rendering and Python-side image resizing.
        Returns (pixmap, scale_factor).
        """
        doc = fitz.open(pdf_path)
        if pageno_idx < 0 or pageno_idx >= len(doc):
            doc.close()
            raise IndexError("Page index out of range")
        
        page = doc[pageno_idx]
        rect = page.rect
        max_dim = max(rect.width, rect.height)
        
        # Scale to max_side capped at ~200 DPI (200/72 = 2.7778)
        target_scale = min(200.0 / 72.0, max_side / max_dim) if max_dim > 0 else 1.0
        mat = fitz.Matrix(target_scale, target_scale)
        
        # Render directly to RGB in C (alpha=False saves 25% RAM)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        doc.close()
        return pix, target_scale
