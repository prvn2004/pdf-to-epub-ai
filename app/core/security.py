import secrets
import re
from pathlib import Path
from fastapi import Request, HTTPException, Response, UploadFile

# Maximum allowed file size per upload (200 MB)
MAX_FILE_SIZE_BYTES = 200 * 1024 * 1024

class SecurityService:
    @staticmethod
    def generate_secure_job_token() -> str:
        """Generate a 24-character cryptographically unguessable job token."""
        return secrets.token_urlsafe(18)

    @staticmethod
    def get_or_create_client_token(request: Request, response: Response = None) -> str:
        """Extract or issue a client session authorization token."""
        token = request.headers.get("X-Client-Token") or request.cookies.get("folio_client_token")
        if not token or len(token) > 64:
            token = secrets.token_urlsafe(24)
            if response:
                response.set_cookie(
                    key="folio_client_token",
                    value=token,
                    max_age=30 * 24 * 3600,
                    httponly=True,
                    samesite="lax"
                )
        return token

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
