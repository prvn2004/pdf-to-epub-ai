import fitz
from typing import Dict, Any
from app.clients.base import BasePDFRenderer

class PyMuPDFRenderer(BasePDFRenderer):
    def get_info(self, pdf_path: str) -> Dict[str, Any]:
        doc = fitz.open(pdf_path)
        info = {"pages": len(doc), "metadata": doc.metadata}
        doc.close()
        return info

    def render_page_pixmap(self, pdf_path: str, pageno_idx: int, dpi: int = 200) -> Any:
        doc = fitz.open(pdf_path)
        if pageno_idx < 0 or pageno_idx >= len(doc):
            doc.close()
            raise IndexError("Page index out of range")
        page = doc[pageno_idx]
        pix = page.get_pixmap(dpi=dpi)
        doc.close()
        return pix
