import time
import json
import re
import requests
from typing import Tuple
from app.clients.base import BaseVisionLLMClient
from app.models.ocr import OCRResult, ImageBox
from app.config import settings

class OpenCodeQwenClient(BaseVisionLLMClient):
    def __init__(self, api_key: str = None, api_url: str = None, model: str = None):
        self.api_key = api_key or settings.OPENCODE_API_KEY
        self.api_url = api_url or settings.OPENCODE_URL
        self.model = model or settings.OPENCODE_MODEL

    def ocr_page(self, image_b64: str, page_size: Tuple[int, int], attempts: int = 3) -> OCRResult:
        if not self.api_key:
            raise RuntimeError("OPENCODE_API_KEY not set. Get one at https://opencode.ai/auth")

        combined_prompt = (
            "You are a precise document converter. Carefully analyze this PDF page image — "
            "study the headlines, numbers, and how every element is placed, so you fully "
            "understand the document structure and content before converting. "
            "Convert the page into clean, well-structured Markdown: "
            "use # / ## / ### for headings matching the document's hierarchy, "
            "**bold** and *italic* for emphasis, > for block quotes, "
            "- or 1. for lists, and markdown tables for tabular data. "
            "Preserve numbers exactly (dates, prices, statistics, page references). "
            "Output ALL visible body text exactly as written — no summarization, no commentary, "
            "no 'here is the text'. "
            "IMPORTANT — EXCLUDE non-content text: page numbers, running headers/footers, "
            "ISBNs, copyright/legal boilerplate, watermark text, and anything outside the "
            "main reading flow. "
            "For each image/photo/chart, give its bounding box pixel coordinates "
            "(x, y, width, height) from the top-left corner of the page image. "
            'Respond with ONLY a JSON object of the form {"markdown": "...", "images": '
            '[{"x":0,"y":0,"width":0,"height":0}]} — no preamble, no markdown fences.'
        )

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": combined_prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}}
                    ]
                }
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.0,
            "max_tokens": 16384,
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        last_err = None
        for attempt in range(attempts):
            try:
                resp = requests.post(self.api_url, json=payload, headers=headers, timeout=180)
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
                backoff = 2 ** attempt + 0.5 * attempt
                time.sleep(backoff)

        raise RuntimeError(last_err or "API: unknown failure")
