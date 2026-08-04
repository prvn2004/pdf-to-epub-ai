import os
import time
import re
from pathlib import Path
from typing import Dict, Any
from app.config import settings
from app.services.pdf_service import PDFService
from app.services.ocr_service import OCRService
from app.services.image_service import ImageService
from app.services.session_service import session_manager

class PipelineService:
    def __init__(self, pdf_service: PDFService = None, ocr_service: OCRService = None):
        self.pdf_service = pdf_service or PDFService()
        self.ocr_service = ocr_service or OCRService()

    def process_pdf(self, job_id: str, pdf_path: str, metadata: dict):
        session = session_manager.get_session(job_id)
        if not session:
            return

        telemetry = {"phases": [], "page_times": [], "image_count": 0}

        try:
            info = self.pdf_service.get_info(pdf_path)
            total = info["pages"]
            session_manager.update_session(job_id, pages_total=total)
            session_manager.emit_event(job_id, "progress", {"phase": "opening", "msg": f"PDF: {total} pages"})

            md_parts = []
            ocr_times = []
            all_crops = []

            for i in range(total):
                pageno = i + 1

                # 1. Render page
                session_manager.emit_event(job_id, "progress", {
                    "phase": "render", "current": pageno, "total": total,
                    "msg": f"Rendering page {pageno}/{total}..."
                })
                t_render = time.time()
                img_b64, page_size, scale, pix = self.pdf_service.render_page_for_ocr(pdf_path, i)
                render_time = time.time() - t_render

                # 2. OCR
                session_manager.emit_event(job_id, "progress", {
                    "phase": "ocr", "current": pageno, "total": total,
                    "msg": f"Luna OCR page {pageno}/{total}..."
                })
                t0 = time.time()
                try:
                    ocr_res = self.ocr_service.process_page(img_b64, page_size, scale)
                    md = ocr_res.markdown
                    image_coords = ocr_res.images
                except Exception as e:
                    md = f"[Page {pageno} — OCR failed: {e}]"
                    image_coords = []

                elapsed = time.time() - t0
                ocr_times.append(elapsed)
                session_manager.update_session(job_id, pages_done=pageno)

                # 3. Crop images
                crops = []
                if image_coords:
                    crops = ImageService.crop_images(job_id, pageno, pix, image_coords)
                    all_crops.extend(crops)
                    telemetry["image_count"] += len(crops)
                    for idx, c in enumerate(crops):
                        cap = c.caption or f"Page {pageno} figure {idx + 1}"
                        md += f'\n\n![{cap}]({c.rel_path})\n'

                # 4. Assemble & save page section incrementally
                md = md.strip()
                md_parts.append(f"## Page {pageno}\n\n{md}")
                self._save_incremental(job_id, f"## Page {pageno}\n\n{md}")

                # 5. Emit page completion event
                session_manager.emit_event(job_id, "page_done", {
                    "pageno": pageno,
                    "total": total,
                    "text": md,
                    "images": len(image_coords),
                    "crops": len(crops),
                    "render_sec": round(render_time, 2),
                    "time_sec": round(elapsed, 1),
                    "cumulative_sec": round(sum(ocr_times), 1),
                })

                telemetry["page_times"].append({
                    "page": pageno, "sec": round(elapsed, 1),
                    "render_sec": round(render_time, 2), "images": len(image_coords)
                })

            # Finalize Markdown
            session_manager.emit_event(job_id, "progress", {"phase": "markdown", "msg": "Finalizing Markdown..."})
            t0 = time.time()
            md_path = self._finalize_markdown(job_id, md_parts, metadata)
            md_time = time.time() - t0

            telemetry["phases"] = [
                {"name": "ocr", "pages": total, "total_sec": round(sum(ocr_times), 1),
                 "avg_sec_per_page": round(sum(ocr_times)/total, 1) if total else 0},
                {"name": "markdown", "sec": round(md_time, 1)},
            ]
            telemetry["total_sec"] = round(sum(p["sec"] for p in telemetry["page_times"]) + md_time, 1)
            
            session_manager.update_session(
                job_id, status="done", telemetry=telemetry, md_path=str(md_path)
            )

            md_size = os.path.getsize(md_path) / 1024
            session_manager.emit_event(job_id, "done", {
                "md_path": f"/download/{job_id}",
                "md_size_kb": round(md_size, 1),
                "total_images": len(all_crops),
                "telemetry": telemetry,
            })

        except Exception as e:
            session_manager.update_session(job_id, status="error", error=str(e))
            session_manager.emit_event(job_id, "error", {"msg": str(e)})

    def _save_incremental(self, job_id: str, page_md: str):
        out_dir = settings.OUTPUTS_DIR / job_id
        out_dir.mkdir(parents=True, exist_ok=True)
        with open(out_dir / "content.md", "a", encoding="utf-8") as f:
            f.write(page_md + "\n")

    def _finalize_markdown(self, job_id: str, md_parts: list, metadata: dict) -> Path:
        out_dir = settings.OUTPUTS_DIR / job_id
        out_dir.mkdir(parents=True, exist_ok=True)
        title = metadata.get("title", "Book")
        author = metadata.get("author", "")
        safe = re.sub(r'[<>:"/\\|?*]', "", title).strip() or "book"
        md_path = out_dir / f"{safe}.md"

        header = [f"# {title}", ""]
        if author and author != "Unknown":
            header += [f"*{author}*", ""]
        content = "\n\n".join(header + md_parts).strip() + "\n"
        md_path.write_text(content, encoding="utf-8")
        return md_path
