import time
import json
import re
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from typing import Tuple
from app.clients.base import BaseVisionLLMClient
from app.models.ocr import OCRResult, ImageBox
from app.config import settings

class OpenCodeQwenClient(BaseVisionLLMClient):
    def __init__(self, api_key: str = None, api_url: str = None, model: str = None):
        self.api_key = api_key or settings.OPENCODE_API_KEY
        self.api_url = api_url or settings.OPENCODE_URL
        self.model = model or settings.OPENCODE_MODEL
        
        # Sockets pool sized dynamically to max workers (min 30 sockets)
        pool_size = max(30, settings.MAX_CONCURRENT_WORKERS)
        self.session = requests.Session()
        adapter = HTTPAdapter(
            pool_connections=pool_size,
            pool_maxsize=pool_size,
            max_retries=Retry(total=2, backoff_factor=0.5, status_forcelist=[502, 503, 504])
        )
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    def ocr_page(self, image_b64: str, page_size: Tuple[int, int], attempts: int = 3) -> OCRResult:
        if not self.api_key:
            raise RuntimeError("OPENCODE_API_KEY not set. Get one at https://opencode.ai/auth")

        combined_prompt = (
            "Convert this PDF page image into clean Markdown. "
            "1. Structure: Use #/##/### headings, **bold**, *italic*, > quotes, lists, and tables matching page layout. "
            "2. Content: Transcribe ALL visible main body text verbatim with exact numbers. No summarization or commentary. "
            "3. Exclude: Omit running headers, running footers, page numbers, and copyright/legal boilerplate. "
            "4. Figures: Provide pixel bounding boxes (x, y, width, height) for any images, photos, or charts. "
            'Respond strictly with JSON: {"markdown": "...", "images": [{"x":0,"y":0,"width":0,"height":0}]}'
        )

        img_mime = "image/webp" if settings.IMAGE_FORMAT.upper() == "WEBP" else "image/jpeg"

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": combined_prompt},
                        {"type": "image_url", "image_url": {"url": f"data:{img_mime};base64,{image_b64}"}}
                    ]
                }
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.0,
            "max_tokens": 4096,  # Optimized for faster Vision LLM prefill and generation speed
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        last_err = None
        for attempt in range(attempts):
            try:
                resp = self.session.post(self.api_url, json=payload, headers=headers, timeout=180)
                if resp.status_code == 200:
                    data = resp.json()
                    try:
                        text = data["choices"][0]["message"]["content"]
                    except (KeyError, IndexError, TypeError):
                        raise RuntimeError(f"Unexpected response: {json.dumps(data, indent=2)[:500]}")
                    
                    text = text.strip()
                    text = re.sub(r"^```(?:json)?\s*", "", text)
                    text = re.sub(r"\s*```$", "", text)
                    
                    start, end = text.find("{"), text.rfind("}")
                    if start >= 0 and end > start:
                        text = text[start:end + 1]
                    
                    parsed = json.loads(text)
                    markdown_str = parsed.get("markdown", "") or parsed.get("html", "")
                    raw_images = parsed.get("images", [])
                    
                    boxes = []
                    for img in raw_images:
                        if isinstance(img, dict):
                            boxes.append(ImageBox(
                                x=int(img.get("x", 0)),
                                y=int(img.get("y", 0)),
                                width=int(img.get("width", 0)),
                                height=int(img.get("height", 0)),
                                caption=str(img.get("caption", ""))
                            ))
                    return OCRResult(markdown=markdown_str, images=boxes)
                elif resp.status_code in (429, 500, 502, 503, 504):
                    last_err = f"API error {resp.status_code} (transient): {resp.text[:200]}"
                else:
                    last_err = f"API error {resp.status_code}: {resp.text[:300]}"
            except (requests.RequestException, json.JSONDecodeError) as e:
                last_err = f"API request failed: {e}"

            if attempt + 1 < attempts:
                backoff = 1.5 ** attempt
                time.sleep(backoff)

        raise RuntimeError(last_err or "API: unknown failure")
