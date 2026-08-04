from typing import Tuple
from app.clients.opencode_client import OpenCodeQwenClient
from app.models.ocr import OCRResult

class OCRService:
    def __init__(self, client: OpenCodeQwenClient = None):
        self.client = client or OpenCodeQwenClient()

    def process_page(self, image_b64: str, page_size: Tuple[int, int], scale: float) -> OCRResult:
        result = self.client.ocr_page(image_b64, page_size)
        
        # If image was downscaled when sent to Vision LLM, map coords back to full-res page
        if scale < 1.0 and scale > 0:
            inv = 1.0 / scale
            for box in result.images:
                box.x = int(box.x * inv)
                box.y = int(box.y * inv)
                box.width = int(box.width * inv)
                box.height = int(box.height * inv)
                
        return result
