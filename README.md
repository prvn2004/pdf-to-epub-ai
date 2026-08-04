# Folio — PDF → EPUB / PDF → Markdown Real-time Converter

A minimalist, Apple-Books-inspired web app that converts PDF books to Markdown (and EPUB) **live** — streaming each page in real time as it's processed.

Powered by **Qwen3.7 Plus** (vision LLM) via the OpenCode Go API. The model natively writes clean Markdown and returns image bounding boxes, which are cropped locally and embedded as markdown image references.

## Features

- 🚀 **Live streaming** — each page appears in the preview as soon as it's converted
- 📖 **Minimalist book-reader UI** — split view: original PDF (left) + live markdown preview (right)
- 🖼️ **Local image cropping** — images are extracted from their bounding-box coordinates and embedded in the markdown
- 📊 **Telemetry panel** — pages done, OCR time, avg/page
- 💾 **Incremental saves** — content is written to disk page-by-page (crash-safe)
- ⬇️ **Markdown download** — final `.md` file with document header

## Setup

1. Install Python 3.10+ and create a venv:
   ```bash
   python -m venv .venv
   .\.venv\Scripts\activate        # Windows
   source .venv/bin/activate       # macOS/Linux
   ```

2. Install dependencies:
   ```bash
   pip install "fastapi[standard]" uvicorn python-dotenv pymupdf pillow requests
   ```

3. Set your OpenCode API key in `.env`:
   ```
   OPENCODE_API_KEY=your-key-here
   ```
   (Get one at https://opencode.ai/auth)

## Run

```bash
python server.py
```

Open http://localhost:8765/ and drop a PDF.

## How it works

```mermaid
graph LR
    PDF -->|render page JPEG| Qwen[Qwen3.7 Plus]
    Qwen -->|markdown JSON| Parse{parse markdown + image coords}
    Parse --> MD[Live markdown preview]
    Parse --> Crop[local crop tool]
    Crop --> Embed[embed ![img] refs]
    MD --> Final[.md file download]
```

Each page is an independent API call (no context accumulation), so both 10-page and 1,000-page books work the same.
