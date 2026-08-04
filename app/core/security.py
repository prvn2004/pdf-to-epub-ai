import re
import uuid
from pathlib import Path
from fastapi import Request, HTTPException, UploadFile

# Maximum allowed file size per upload (200 MB)
MAX_FILE_SIZE_BYTES = 200 * 1024 * 1024

class SecurityService:
    @staticmethod
    def get_client_session_id(request: Request) -> str:
        """Extract or generate a client session ID for workspace isolation."""
        client_id = request.headers.get("X-Client-Session-ID") or request.cookies.get("folio_client_id")
        if not client_id or len(client_id) > 64:
            client_id = uuid.uuid4().hex
        return client_id

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Sanitize filenames to prevent path traversal or invalid filesystem characters."""
        if not filename:
            return "document.pdf"
        safe = Path(filename).name
        safe = re.sub(r'[^a-zA-Z0-9_\-\.]', '_', safe)
        if not safe.lower().endswith(".pdf"):
            safe += ".pdf"
        return safe

    @staticmethod
    async def validate_pdf_upload(file: UploadFile) -> bytes:
        """Validate PDF magic bytes (%PDF-) and enforce file size limits."""
        content = await file.read()
        
        if len(content) > MAX_FILE_SIZE_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"File size exceeds maximum allowed limit of {MAX_FILE_SIZE_BYTES // (1024*1024)} MB."
            )
        
        # Check PDF Magic Bytes header (%PDF-)
        if not content.startswith(b"%PDF-"):
            raise HTTPException(
                status_code=400,
                detail="Invalid file format. Only valid PDF files with %PDF- header are accepted."
            )
            
        return content

security_service = SecurityService()
