import pytest
from app.services.session_service import session_manager

def test_session_lifecycle():
    job_id = "test_job_123"
    client_id = "client_abc"
    
    # 1. Create session
    sess = session_manager.create_session(job_id, client_id=client_id, title="Test Title")
    assert sess["job_id"] == job_id
    assert sess["client_id"] == client_id
    assert sess["status"] == "processing"

    # 2. Save page result
    page_data = {"pageno": 1, "text": "Sample OCR markdown content", "images": 0, "crops": 0}
    session_manager.save_page_result(job_id, 1, page_data)
    
    cached = session_manager.get_valid_cached_pages(job_id)
    assert 1 in cached
    assert cached[1]["text"] == "Sample OCR markdown content"

    # 3. Verify owner authorization
    assert session_manager.verify_job_owner(job_id, client_id) is True
    assert session_manager.verify_job_owner(job_id, "wrong_client") is False

    # 4. Delete session
    session_manager.delete_session(job_id)
    assert session_manager.get_session(job_id) is None
