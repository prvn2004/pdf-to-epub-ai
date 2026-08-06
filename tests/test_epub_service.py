import pytest
from app.services.epub_service import EPUBService

def test_markdown_to_xhtml():
    service = EPUBService()
    md = "# Title\n\nThis is **bold** and *italic* text.\n\n![Figure 1](/crops/job1/page1_img0.jpg)"
    
    xhtml, images = service._markdown_to_xhtml(md)
    
    assert "<h1>Title</h1>" in xhtml
    assert "<strong>bold</strong>" in xhtml
    assert "<em>italic</em>" in xhtml
    assert 'src="crops/page1_img0.jpg"' in xhtml
    assert len(images) == 1
    assert images[0]["filename"] == "page1_img0.jpg"
