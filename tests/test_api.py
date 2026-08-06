import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_api_upload_invalid_file():
    response = client.post(
        "/api/upload",
        files={"file": ("test.txt", b"plain text file", "text/plain")}
    )
    assert response.status_code == 400
    assert "Invalid file format" in response.json()["detail"]

def test_api_upload_valid_pdf():
    pdf_bytes = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF"
    response = client.post(
        "/api/upload",
        files={"file": ("test.pdf", pdf_bytes, "application/pdf")},
        data={"title": "Test Book", "author": "Test Author"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "job_id" in data
    assert data["status"] == "started"

def test_get_session_not_found():
    response = client.get("/api/session/non_existent_job_id")
    # Non-existent or unauthorized sessions properly return 403 or 404 security responses
    assert response.status_code in (403, 404)
