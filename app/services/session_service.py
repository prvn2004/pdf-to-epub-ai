import json
import threading
from pathlib import Path
from typing import Dict, Any, List, Optional
from app.config import settings

class SessionService:
    def __init__(self):
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def create_session(self, job_id: str) -> Dict[str, Any]:
        with self._lock:
            queue: List[Dict[str, Any]] = []
            session_data = {
                "job_id": job_id,
                "status": "processing",
                "pages_total": 0,
                "pages_done": 0,
                "completed_pages": {},  # pageno -> page_dict
                "queue": queue,
                "telemetry": {},
                "md_path": None,
                "error": None,
            }
            self._sessions[job_id] = session_data
            self._persist_session_meta(job_id)
            return session_data

    def get_session(self, job_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            if job_id not in self._sessions:
                loaded = self._load_session_from_disk(job_id)
                if loaded:
                    self._sessions[job_id] = loaded
            return self._sessions.get(job_id)

    def emit_event(self, job_id: str, event: str, data: dict):
        with self._lock:
            sess = self._sessions.get(job_id)
            if sess and "queue" in sess:
                sess["queue"].append({"event": event, "data": data})

    def update_session(self, job_id: str, **kwargs):
        with self._lock:
            sess = self._sessions.get(job_id)
            if sess:
                sess.update(kwargs)
                self._persist_session_meta(job_id)

    def save_page_result(self, job_id: str, pageno: int, page_data: dict):
        with self._lock:
            sess = self._sessions.get(job_id)
            if sess:
                sess["completed_pages"][pageno] = page_data
                sess["pages_done"] = len(sess["completed_pages"])

        pages_dir = settings.OUTPUTS_DIR / job_id / "pages"
        pages_dir.mkdir(parents=True, exist_ok=True)
        page_file = pages_dir / f"page_{pageno}.json"
        page_file.write_text(json.dumps(page_data, ensure_ascii=False, indent=2), encoding="utf-8")
        
        self._persist_session_meta(job_id)

    def load_cached_pages(self, job_id: str) -> Dict[int, dict]:
        pages_dir = settings.OUTPUTS_DIR / job_id / "pages"
        if not pages_dir.exists():
            return {}

        cached = {}
        for f in pages_dir.glob("page_*.json"):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                pageno = data.get("pageno")
                if pageno:
                    cached[pageno] = data
            except Exception:
                pass
        return cached

    def is_valid_page(self, page_data: dict) -> bool:
        """Check if a page result is a valid successful OCR page (not failed/stub)."""
        if not page_data or not isinstance(page_data, dict):
            return False
        text = page_data.get("text", "")
        if not text or "OCR failed" in text or "Content Missing" in text:
            return False
        return True

    def get_valid_cached_pages(self, job_id: str) -> Dict[int, dict]:
        all_cached = self.load_cached_pages(job_id)
        valid = {}
        for pageno, data in all_cached.items():
            if self.is_valid_page(data):
                valid[pageno] = data
        return valid

    def populate_queue_from_history(self, job_id: str):
        """Populate event queue with all historical page_done and status events if queue is empty."""
        with self._lock:
            sess = self._sessions.get(job_id)
            if not sess:
                return

            if not sess.get("queue"):
                queue = []
                cached = self.get_valid_cached_pages(job_id)
                sorted_pages = sorted(cached.keys())

                for pageno in sorted_pages:
                    queue.append({"event": "page_done", "data": cached[pageno]})

                status = sess.get("status")
                if status == "done":
                    out_dir = settings.OUTPUTS_DIR / job_id
                    mds = list(out_dir.glob("*.md")) if out_dir.exists() else []
                    md_path = f"/download/{job_id}" if mds else ""
                    queue.append({"event": "done", "data": {
                        "md_path": md_path,
                        "telemetry": sess.get("telemetry", {}),
                    }})
                elif status in ("error", "incomplete"):
                    queue.append({"event": "error", "data": {
                        "msg": sess.get("error") or "Processing incomplete — some pages require retry."
                    }})

                sess["queue"] = queue

    def _persist_session_meta(self, job_id: str):
        sess = self._sessions.get(job_id)
        if not sess:
            return
        
        meta_dir = settings.OUTPUTS_DIR / job_id
        meta_dir.mkdir(parents=True, exist_ok=True)
        meta_file = meta_dir / "session.json"
        
        copy_data = {
            "job_id": sess.get("job_id"),
            "status": sess.get("status"),
            "pages_total": sess.get("pages_total"),
            "pages_done": len(sess.get("completed_pages", {})),
            "telemetry": sess.get("telemetry"),
            "md_path": sess.get("md_path"),
            "error": sess.get("error"),
        }
        meta_file.write_text(json.dumps(copy_data, indent=2), encoding="utf-8")

    def _load_session_from_disk(self, job_id: str) -> Optional[Dict[str, Any]]:
        meta_file = settings.OUTPUTS_DIR / job_id / "session.json"
        if not meta_file.exists():
            return None
        try:
            meta = json.loads(meta_file.read_text(encoding="utf-8"))
            valid_pages = self.get_valid_cached_pages(job_id)
            meta["completed_pages"] = valid_pages
            meta["pages_done"] = len(valid_pages)
            meta["queue"] = []
            
            # Pre-populate event queue with page_done history
            sorted_pages = sorted(valid_pages.keys())
            for pageno in sorted_pages:
                meta["queue"].append({"event": "page_done", "data": valid_pages[pageno]})
            
            if meta.get("status") == "done":
                meta["queue"].append({"event": "done", "data": {
                    "md_path": f"/download/{job_id}",
                    "telemetry": meta.get("telemetry", {}),
                }})

            return meta
        except Exception as e:
            print(f"[SessionService] Error loading session {job_id}: {e}")
            return None

session_manager = SessionService()
