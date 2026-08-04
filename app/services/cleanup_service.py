import time
from pathlib import Path
from app.config import settings
from app.services.session_service import session_manager

class CleanupService:
    @staticmethod
    def cleanup_expired_pdf_uploads():
        """
        Deletes uploaded source PDF files from uploads/ if the job completed more than 
        PDF_RETENTION_SECONDS (10 minutes) ago.
        """
        now = time.time()
        retention = settings.PDF_RETENTION_SECONDS

        if not settings.UPLOADS_DIR.exists():
            return

        for pdf_file in settings.UPLOADS_DIR.glob("*.pdf"):
            try:
                job_id = pdf_file.stem
                sess = session_manager.get_session(job_id)
                
                # If session status is done, check completion age
                if sess and sess.get("status") == "done":
                    file_age = now - pdf_file.stat().st_mtime
                    if file_age >= retention:
                        pdf_file.unlink(missing_ok=True)
                        print(f"[CleanupService] Purged PDF upload after retention window (age: {int(file_age)}s): {pdf_file.name}")
            except Exception as e:
                print(f"[CleanupService warn] Error checking {pdf_file}: {e}")

cleanup_service = CleanupService()
