import time
import shutil
import threading
from pathlib import Path
from app.config import settings
from app.services.session_service import session_manager

class TTLService:
    def __init__(self, ttl_seconds: int = 3600, check_interval_seconds: int = 300):
        self.ttl_seconds = ttl_seconds  # Auto-purge inactive jobs after 1 hour (3600s)
        self.check_interval = check_interval_seconds
        self._thread = None
        self._running = False

    def start_background_cleanup(self):
        """Start background TTL daemon thread."""
        if not self._running:
            self._running = True
            self._thread = threading.Thread(target=self._cleanup_loop, daemon=True)
            self._thread.start()

    def _cleanup_loop(self):
        while self._running:
            try:
                self.purge_expired_jobs()
            except Exception as e:
                print(f"[TTLService warn] Error during TTL cleanup: {e}")
            time.sleep(self.check_interval)

    def purge_expired_jobs(self):
        """Purge outputs, crops, uploads, and metadata for jobs inactive for > ttl_seconds."""
        now = time.time()
        if not settings.OUTPUTS_DIR.exists():
            return

        purged_count = 0
        for meta_dir in list(settings.OUTPUTS_DIR.iterdir()):
            if meta_dir.is_dir():
                job_id = meta_dir.name
                session_file = meta_dir / "session.json"
                
                # Determine last modified time
                mtime = session_file.stat().st_mtime if session_file.exists() else meta_dir.stat().st_mtime
                age = now - mtime

                if age > self.ttl_seconds:
                    session_manager.delete_session(job_id)
                    purged_count += 1
                    print(f"[TTLService] Purged stale job {job_id} after {int(age)}s of inactivity.")

        if purged_count > 0:
            print(f"[TTLService] Cleaned up {purged_count} expired job(s) from server disk.")

ttl_service = TTLService()
