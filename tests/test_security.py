import asyncio
import pytest
from fastapi import HTTPException
from app.core.security import security_service

def test_generate_secure_job_token():
    token1 = security_service.generate_secure_job_token()
    token2 = security_service.generate_secure_job_token()
    assert isinstance(token1, str)
    assert len(token1) >= 20
    assert token1 != token2

def test_sanitize_filename():
    assert security_service.sanitize_filename("test.pdf") == "test.pdf"
    assert security_service.sanitize_filename("../../../etc/passwd") == "passwd.pdf"
    assert security_service.sanitize_filename("my book?.pdf") == "my_book_.pdf"

def test_validate_pdf_upload_invalid_bytes():
    class DummyUploadFile:
        async def read(self):
            return b"NOT_A_PDF_HEADER"

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(security_service.validate_pdf_upload(DummyUploadFile()))
    assert exc_info.value.status_code == 400

def test_validate_pdf_upload_valid_bytes():
    class DummyUploadFile:
        async def read(self):
            return b"%PDF-1.5 fake pdf content"

    content = asyncio.run(security_service.validate_pdf_upload(DummyUploadFile()))
    assert content.startswith(b"%PDF-")
