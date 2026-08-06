import os
import gc
import time
import re
import threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, List
from app.config import settings
from app.services.pdf_service import PDFService
from app.services.ocr_service import OCRService
from app.services.image_service import ImageService
from app.services.session_service import session_manager

# Global Bounded Semaphore to cap total concurrent LLM HTTP requests across all users (max 20)
GLOBAL_LLM_SEMAPHORE = threading.BoundedSemaphore(value=20)

class PipelineService:
    def __init__(self, pdf_service: PDFService = None, ocr_service: OCRService = None, max_workers: int = None):
        self.pdf_service = pdf_service or PDFService()
        self.ocr_service = ocr_service or OCRService()
        self.max_workers = max_workers or settings.MAX_CONCURRENT_WORKERS

    def process_pdf(self, job_id: str, pdf_path: str, metadata: dict):
        session = session_manager.get_session(job_id)
        if not session:
            return

        job_start_time = time.time()
        telemetry = {
            "title": metadata.get("title", "Book"),
            "author": metadata.get("author", ""),
            "phases": [],
            "page_times": [],
            "image_count": 0
        }

        try:
            info = self.pdf_service.get_info(pdf_path)
            total = info["pages"]
            session_manager.update_session(job_id, pages_total=total, status="processing")
            session_manager.emit_event(job_id, "progress", {
                "phase": "opening",
                "msg": f"PDF: {total} pages | Workers: {self.max_workers}"
            })

            valid_cached = session_manager.get_valid_cached_pages(job_id)
            pages_to_process = [i for i in range(total) if (i + 1) not in valid_cached]

            for pageno in sorted(valid_cached.keys()):
                p_data = valid_cached[pageno]
                session_manager.emit_event(job_id, "page_done", p_data)

            ocr_times = [p.get("time_sec", 0.0) for p in valid_cached.values()]

            if pages_to_process:
                session_manager.emit_event(job_id, "progress", {
                    "phase": "ocr",
                    "msg": f"Processing {len(valid_cached)} of {total} pages completed..."
                })

                with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                    futures = {}
                    for i in pages_to_process:
                        if session_manager.is_paused(job_id):
                            session_manager.emit_event(job_id, "progress", {
                                "phase": "paused", "msg": "⏸️ Job paused by user. Click Resume to continue."
                            })
                            return

                        fut = executor.submit(self._process_single_page, job_id, pdf_path, i, total, job_start_time)
                        futures[fut] = i + 1

                    for future in as_completed(futures):
                        pageno = futures[future]
                        if session_manager.is_paused(job_id):
                            return

                        try:
                            res = future.result()
                            if res:
                                valid_cached[pageno] = res
                                ocr_times.append(res.get("time_sec", 0.0))
                                telemetry["image_count"] += res.get("crops", 0)
                                telemetry["page_times"].append({
                                    "page": pageno,
                                    "sec": res.get("time_sec", 0.0),
                                    "render_sec": res.get("render_sec", 0.0),
                                    "images": res.get("images", 0)
                                })
                        except Exception as exc:
                            print(f"[pipeline error] Page {pageno} failed: {exc}")

            if session_manager.is_paused(job_id):
                return

            still_missing = [p for p in range(1, total + 1) if p not in valid_cached]

            if still_missing:
                session_manager.update_session(
                    job_id,
                    status="incomplete",
                    error=f"Processing incomplete — {len(still_missing)} page(s) missing or failed. Click Resume to retry."
                )
                session_manager.emit_event(job_id, "error", {
                    "msg": f"⚠️ Incomplete: {len(still_missing)} page(s) missing or failed. Click Resume to retry."
                })
                return

            session_manager.emit_event(job_id, "progress", {"phase": "markdown", "msg": "Finalizing document..."})
            t0 = time.time()

            sorted_md_parts = []
            for pageno in range(1, total + 1):
                p_info = valid_cached.get(pageno, {})
                text = p_info.get("text", f"[Page {pageno} — Content Missing]")
                sorted_md_parts.append(f"## Page {pageno}\n\n{text.strip()}")

            md_path = self._finalize_markdown(job_id, sorted_md_parts, metadata)
            md_time = time.time() - t0

            telemetry["phases"] = [
                {
                    "name": "ocr",
                    "pages": total,
                    "total_sec": round(sum(ocr_times), 1),
                    "avg_sec_per_page": round(sum(ocr_times) / total, 1) if total else 0
                },
                {"name": "markdown", "sec": round(md_time, 1)},
            ]
            telemetry["total_sec"] = round(time.time() - job_start_time, 1)

            session_manager.update_session(
                job_id, status="done", telemetry=telemetry, md_path=str(md_path)
            )

            # Reclaim source upload PDF immediately on 100% completion
            if settings.CLEANUP_UPLOAD_ON_COMPLETE:
                try:
                    p = Path(pdf_path)
                    if p.exists():
                        p.unlink()
                except Exception as cleanup_err:
                    print(f"[pipeline cleanup warn] {cleanup_err}")

            gc.collect()

            md_size = os.path.getsize(md_path) / 1024
            session_manager.emit_event(job_id, "done", {
                "md_path": f"/download/{job_id}",
                "md_size_kb": round(md_size, 1),
                "total_images": telemetry["image_count"],
                "telemetry": telemetry,
            })

        except Exception as e:
            session_manager.update_session(job_id, status="error", error=str(e))
            session_manager.emit_event(job_id, "error", {"msg": str(e)})

    def _process_single_page(self, job_id: str, pdf_path: str, page_idx: int, total: int, job_start_time: float, max_attempts: int = 2) -> dict:
        pageno = page_idx + 1
        pix = None
        img_b64 = None

        if session_manager.is_paused(job_id):
            return {}

        # 1. Non-blocking C-level matrix rendering (<10ms) OUTSIDE LLM semaphore lock
        t_render = time.time()
        img_b64, page_size, scale, pix = self.pdf_service.render_page_for_ocr(pdf_path, page_idx)
        render_time = time.time() - t_render

        # 2. Acquire global rate-limiting semaphore ONLY during Vision LLM HTTP request
        t0 = time.time()
        ocr_res = None
        last_exc = None

        for attempt in range(max_attempts):
            if session_manager.is_paused(job_id):
                return {}

            try:
                # Wrap ONLY the network request inside the semaphore lock
                with GLOBAL_LLM_SEMAPHORE:
                    ocr_res = self.ocr_service.process_page(img_b64, page_size, scale)
                break
            except Exception as e:
                last_exc = e
                if attempt + 1 < max_attempts:
                    time.sleep(1.0)

        if not ocr_res:
            raise RuntimeError(f"OCR failed for page {pageno} after {max_attempts} attempts: {last_exc}")

        md = ocr_res.markdown
        image_coords = ocr_res.images
        elapsed = time.time() - t0
        cumulative_elapsed = time.time() - job_start_time

        # 3. Crop images locally OUTSIDE LLM semaphore lock
        crops = []
        if image_coords:
            crops = ImageService.crop_images(job_id, pageno, pix, image_coords)
            for idx, c in enumerate(crops):
                cap = c.caption or f"Page {pageno} figure {idx + 1}"
                md += f'\n\n![{cap}]({c.rel_path})\n'

        md = md.strip()
        page_data = {
            "pageno": pageno,
            "total": total,
            "text": md,
            "images": len(image_coords),
            "crops": len(crops),
            "render_sec": round(render_time, 2),
            "time_sec": round(elapsed, 1),
            "cumulative_sec": round(cumulative_elapsed, 1),
        }

        session_manager.save_page_result(job_id, pageno, page_data)
        session_manager.emit_event(job_id, "page_done", page_data)

        pix = None
        img_b64 = None
        return page_data

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
