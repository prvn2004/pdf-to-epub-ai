import threading
from typing import Dict, Any, List, Optional
from app.models.session import JobSession

class SessionService:
    def __init__(self):
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def create_session(self, job_id: str) -> Dict[str, Any]:
        with self._lock:
            queue: List[Dict[str, Any]] = []
            session_data = {
                "status": "processing",
                "pages_total": 0,
                "pages_done": 0,
                "queue": queue,
                "telemetry": {},
                "md_path": None,
                "error": None,
            }
            self._sessions[job_id] = session_data
            return session_data

    def get_session(self, job_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
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

session_manager = SessionService()
