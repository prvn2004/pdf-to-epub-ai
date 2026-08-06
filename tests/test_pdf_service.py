import pytest
from unittest.mock import MagicMock
from app.services.pdf_service import PDFService

@pytest.fixture
def mock_renderer():
    renderer = MagicMock()
    renderer.get_info.return_value = {"pages": 5, "title": "Mock PDF"}

    # Mock PyMuPDF Pixmap
    mock_pix = MagicMock()
    mock_pix.width = 100
    mock_pix.height = 200
    mock_pix.samples = b"\x00" * (100 * 200 * 3)
    renderer.render_page_pixmap.return_value = (mock_pix, 1.0)
    return renderer

def test_pdf_service_get_info(mock_renderer):
    service = PDFService(renderer=mock_renderer)
    info = service.get_info("dummy.pdf")
    assert info["pages"] == 5
    assert info["title"] == "Mock PDF"
    mock_renderer.get_info.assert_called_once_with("dummy.pdf")

def test_encode_pixmap_for_ocr(mock_renderer):
    service = PDFService(renderer=mock_renderer)
    mock_pix = MagicMock()
    mock_pix.width = 50
    mock_pix.height = 50
    mock_pix.samples = b"\xff" * (50 * 50 * 3)

    img_b64, page_size = service.encode_pixmap_for_ocr(mock_pix)
    assert isinstance(img_b64, str)
    assert len(img_b64) > 0
    assert page_size == (50, 50)

def test_render_page_preview_webp(mock_renderer):
    service = PDFService(renderer=mock_renderer)
    data = service.render_page_preview_webp("dummy.pdf", 0)
    assert isinstance(data, bytes)
    assert len(data) > 0
