"""
Folio — PDF → Markdown Live
============================
Powered by Qwen3.7 Plus via OpenCode Go API.
The model natively generates Markdown + image coordinates; images are
cropped locally and embedded as markdown image references.
"""

import os, sys, time, json, base64, io, uuid, threading, re
from pathlib import Path
from datetime import datetime
from typing import Optional

os.environ["GRPC_VERBOSITY"] = "ERROR"
os.environ["GLOG_minloglevel"] = "2"

from dotenv import load_dotenv
BASE = Path(__file__).parent
load_dotenv(BASE / ".env")

import fitz
from PIL import Image, ImageDraw
import requests
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import HTMLResponse, FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import asyncio

app = FastAPI(title="Folio — PDF to Markdown")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ── Paths ──
UPLOADS = BASE / "uploads"
OUTPUTS = BASE / "outputs"
CROPS = BASE / "crops"
UPLOADS.mkdir(exist_ok=True)
OUTPUTS.mkdir(exist_ok=True)
CROPS.mkdir(exist_ok=True)

# ── OpenCode Go API (Qwen3.7 Plus) ──
LUNA_URL = "https://opencode.ai/zen/go/v1/chat/completions"  # Go subscription
LUNA_MODEL = "qwen3.7-plus"
LUNA_KEY = os.getenv("OPENCODE_API_KEY", "")

# ── Session store ──
sessions: dict = {}

# Vision input cap (longest side, px). Large images → upstream 400.
MAX_IMAGE_SIDE = 1568


# ═══════════════════════════════════════════════════════════════════════════════
#  OCR ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

def ocr_page_luna(image_b64: str, page_size: tuple, attempts: int = 3) -> dict:
    """Send page to Qwen3.7 Plus via Go Chat Completions API, get structured JSON.
    The model natively writes Markdown (no HTML round-trip).
    Retries on transient failures (rate limits, upstream blips)."""
    if not LUNA_KEY:
        raise RuntimeError("OPENCODE_API_KEY not set. Get one at https://opencode.ai/auth")

    h, w = page_size

    combined = (
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

    # Chat Completions format: "messages" + "response_format"
    payload = {
        "model": LUNA_MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": combined},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}}
                ]
            }
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.0,
        "max_tokens": 16384,
    }

    headers = {
        "Authorization": f"Bearer {LUNA_KEY}",
        "Content-Type": "application/json"
    }

    last_err = None
    for attempt in range(attempts):
        try:
            resp = requests.post(LUNA_URL, json=payload, headers=headers, timeout=180)
            if resp.status_code == 200:
                data = resp.json()
                # Chat Completions: choices[0].message.content
                try:
                    text = data["choices"][0]["message"]["content"]
                except (KeyError, IndexError, TypeError):
                    raise RuntimeError(f"Unexpected response: {json.dumps(data, indent=2)[:500]}")
                text = text.strip()
                # Strip any markdown fences if the model wrapped the JSON
                text = re.sub(r"^```(?:json)?\s*", "", text)
                text = re.sub(r"\s*```$", "", text)
                # Extract the JSON object (lenient: find first { ... last })
                start, end = text.find("{"), text.rfind("}")
                if start >= 0 and end > start:
                    text = text[start:end + 1]
                return json.loads(text)
            elif resp.status_code in (429, 500, 502, 503, 504):
                last_err = f"API error {resp.status_code} (transient): {resp.text[:200]}"
            else:
                last_err = f"API error {resp.status_code}: {resp.text[:300]}"
        except (requests.RequestException, json.JSONDecodeError) as e:
            last_err = f"API request failed: {e}"

        if attempt + 1 < attempts:
            backoff = 2 ** attempt + 0.5 * attempt  # 0.5s, 2.5s, ...
            time.sleep(backoff)

    raise RuntimeError(last_err or "API: unknown failure")


# ═══════════════════════════════════════════════════════════════════════════════
#  IMAGE CROP TOOL
# ═══════════════════════════════════════════════════════════════════════════════

# Max pixel dimension for saved crops (downscaled). Images bigger than this
# are scaled down on save — keeps the EPUB/markdown lightweight and prevents
# the browser from loading enormous full-page crops.
MAX_CROP_SIDE = 1200


def crop_images(job_id: str, pageno: int, page_pix, images: list) -> list:
    """Crop images from page using coordinates, save to disk, return paths.

    Coordinates are expected in the FULL-RES page space (already scaled back
    from the model's downscaled view by the caller). Invalid or degenerate
    boxes are skipped.
    """
    pw, ph = page_pix.width, page_pix.height
    page_img = Image.frombytes("RGB", [pw, ph], page_pix.samples)
    crop_dir = CROPS / job_id
    crop_dir.mkdir(exist_ok=True)

    crops = []
    for idx, img_info in enumerate(images):
        try:
            x = int(img_info.get("x", 0))
            y = int(img_info.get("y", 0))
            w = int(img_info.get("width", 0))
            h = int(img_info.get("height", 0))

            # Reject degenerate/invalid boxes
            if w <= 2 or h <= 2 or x >= pw or y >= ph:
                continue

            # Clamp to page bounds
            x = max(0, min(x, pw - 1))
            y = max(0, min(y, ph - 1))
            w = max(1, min(w, pw - x))
            h = max(1, min(h, ph - y))

            cropped = page_img.crop((x, y, x + w, y + h))

            # Downscale oversized crops so they're web-friendly
            max_side = max(cropped.size)
            if max_side > MAX_CROP_SIDE:
                ratio = MAX_CROP_SIDE / max_side
                cropped = cropped.resize(
                    (int(cropped.width * ratio), int(cropped.height * ratio)),
                    Image.LANCZOS,
                )

            fname = f"page{pageno}_img{idx}.jpg"
            fpath = crop_dir / fname
            cropped.save(fpath, format="JPEG", quality=85, optimize=True)

            crops.append({
                "path": str(fpath),
                "rel_path": f"/crops/{job_id}/{fname}",
                "caption": img_info.get("caption", ""),
                "x": x, "y": y, "width": w, "height": h,
                "px_width": cropped.width, "px_height": cropped.height,
            })
        except Exception as e:
            print(f"  [crop warn] page {pageno} img {idx}: {e}")

    return crops


# ═══════════════════════════════════════════════════════════════════════════════
#  PROCESSING PIPELINE
# ═══════════════════════════════════════════════════════════════════════════════

def process_pdf(job_id: str, pdf_path: str, metadata: dict):
    """Full pipeline: PDF → page-by-page OCR → Markdown."""
    session = sessions[job_id]
    queue = session["queue"]
    telemetry = {"phases": [], "page_times": [], "image_count": 0}

    try:
        doc = fitz.open(pdf_path)
        total = len(doc)
        session["pages_total"] = total
        _emit(queue, "progress", {"phase": "opening", "msg": f"PDF: {total} pages"})

        md_parts = []
        ocr_times = []
        all_crops = []

        for i in range(total):
            pageno = i + 1

            # 1) Render page to JPEG
            _emit(queue, "progress", {"phase": "render", "current": pageno, "total": total,
                                       "msg": f"Rendering page {pageno}/{total}..."})
            t_render = time.time()
            page = doc[i]
            pix = page.get_pixmap(dpi=200)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            # Cap longest side so the API never sees an oversized image (upstream 400s)
            scale = min(1.0, MAX_IMAGE_SIDE / max(img.size))
            if scale < 1.0:
                img = img.resize((int(img.width * scale), int(img.height * scale)), Image.LANCZOS)
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=78)
            img_b64 = base64.b64encode(buf.getvalue()).decode()
            render_time = time.time() - t_render

            # 2) OCR with Luna
            _emit(queue, "progress", {"phase": "ocr", "current": pageno, "total": total,
                                       "msg": f"Luna OCR page {pageno}/{total}..."})
            t0 = time.time()
            try:
                result = ocr_page_luna(img_b64, (pix.height, pix.width))
                md = result.get("markdown", "") or result.get("html", "")
                image_coords = result.get("images", [])
                # Model saw the RESIZED image — map coords back to full-res pixmap
                if scale < 1.0:
                    inv = 1.0 / scale
                    for c in image_coords:
                        c["x"] = int(c.get("x", 0) * inv)
                        c["y"] = int(c.get("y", 0) * inv)
                        c["width"] = int(c.get("width", 0) * inv)
                        c["height"] = int(c.get("height", 0) * inv)
            except Exception as e:
                md = f"[Page {pageno} — OCR failed: {e}]"
                image_coords = []

            elapsed = time.time() - t0
            ocr_times.append(elapsed)
            session["pages_done"] = pageno

            # 3) Crop images from this page, embed as markdown references
            crops = []
            if image_coords:
                crops = crop_images(job_id, pageno, pix, image_coords)
                all_crops.extend(crops)
                telemetry["image_count"] += len(crops)
                for idx, c in enumerate(crops):
                    cap = c.get("caption", "") or f"Page {pageno} figure {idx + 1}"
                    md += f'\n\n![{cap}]({c["rel_path"]})\n'

            # 4) Assemble page section
            md = md.strip()
            md_parts.append(f"## Page {pageno}\n\n{md}")

            # 5) Save incrementally (crash-safe: content is on disk page by page)
            _save_incremental(job_id, f"## Page {pageno}\n\n{md}")

            # 6) Emit to frontend
            _emit(queue, "page_done", {
                "pageno": pageno,
                "total": total,
                "text": md,
                "images": len(image_coords),
                "crops": len(crops),
                "render_sec": round(render_time, 2),
                "time_sec": round(elapsed, 1),
                "cumulative_sec": round(sum(ocr_times), 1),
            })

            telemetry["page_times"].append({
                "page": pageno, "sec": round(elapsed, 1),
                "render_sec": round(render_time, 2), "images": len(image_coords)
            })

        doc.close()

        # ── Finalize Markdown ──
        _emit(queue, "progress", {"phase": "markdown", "msg": "Finalizing Markdown..."})
        t0 = time.time()
        md_path = _finalize_markdown(job_id, md_parts, metadata)
        md_time = time.time() - t0

        # ── Done ──
        telemetry["phases"] = [
            {"name": "ocr", "pages": total, "total_sec": round(sum(ocr_times), 1),
             "avg_sec_per_page": round(sum(ocr_times)/total, 1) if total else 0},
            {"name": "markdown", "sec": round(md_time, 1)},
        ]
        telemetry["total_sec"] = round(sum(p["sec"] for p in telemetry["page_times"]) + md_time, 1)
        session["telemetry"] = telemetry
        session["status"] = "done"
        session["md_path"] = str(md_path)

        md_size = os.path.getsize(md_path) / 1024
        _emit(queue, "done", {
            "md_path": f"/download/{job_id}",
            "md_size_kb": round(md_size, 1),
            "total_images": len(all_crops),
            "telemetry": telemetry,
        })

    except Exception as e:
        session["status"] = "error"
        session["error"] = str(e)
        _emit(queue, "error", {"msg": str(e)})


def _save_incremental(job_id: str, page_md: str):
    """Append page content to accumulating markdown file."""
    out_dir = OUTPUTS / job_id
    out_dir.mkdir(exist_ok=True)
    with open(out_dir / "content.md", "a", encoding="utf-8") as f:
        f.write(page_md + "\n")


def _finalize_markdown(job_id: str, md_parts: list, metadata: dict) -> Path:
    """Write the final Markdown file with a document header."""
    out_dir = OUTPUTS / job_id
    out_dir.mkdir(exist_ok=True)
    title = metadata.get("title", "Book")
    author = metadata.get("author", "")
    safe = re.sub(r'[<>:"/\\|?*]', "", title).strip() or "book"
    md_path = out_dir / f"{safe}.md"

    header = [f"# {title}", ""]
    if author and author != "Unknown":
        header += [f"*{author}*", ""]
    content = "\n\n".join(header + md_parts).strip() + "\n"
    md_path.write_text(content, encoding="utf-8")
    return md_path


def _emit(queue: list, event: str, data: dict):
    queue.append({"event": event, "data": data})


# ═══════════════════════════════════════════════════════════════════════════════
#  API ROUTES
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/", response_class=HTMLResponse)
async def home():
    return (BASE / "index.html").read_text(encoding="utf-8")


@app.post("/api/upload")
async def upload(file: UploadFile = File(...), title: str = Form(""), author: str = Form("")):
    job_id = uuid.uuid4().hex[:12]
    pdf_path = UPLOADS / f"{job_id}.pdf"
    content = await file.read()
    pdf_path.write_bytes(content)

    queue = []
    sessions[job_id] = {
        "status": "processing",
        "pages_total": 0,
        "pages_done": 0,
        "queue": queue,
        "telemetry": {},
        "md_path": None,
        "error": None,
    }

    metadata = {
        "filename": file.filename,
        "title": title or Path(file.filename).stem.replace("_", " ").title(),
        "author": author or "Unknown",
    }

    thread = threading.Thread(target=process_pdf, args=(job_id, str(pdf_path), metadata))
    thread.start()
    return {"job_id": job_id, "status": "started"}


@app.get("/api/stream/{job_id}")
async def stream(job_id: str):
    if job_id not in sessions:
        async def err(): yield f"event: error\ndata: {json.dumps({'msg':'Job not found'})}\n\n"
        return StreamingResponse(err(), media_type="text/event-stream")

    queue = sessions[job_id]["queue"]

    async def generate():
        last_idx = 0
        done_sent = False
        while True:
            while last_idx < len(queue):
                evt = queue[last_idx]
                last_idx += 1
                yield f"event: {evt['event']}\ndata: {json.dumps(evt['data'])}\n\n"
                if evt["event"] in ("done", "error"):
                    done_sent = True
            if done_sent:
                break
            await asyncio.sleep(0.2)

    return StreamingResponse(generate(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.get("/api/preview/{job_id}/{page}")
async def preview_page(job_id: str, page: int):
    pdf_path = UPLOADS / f"{job_id}.pdf"
    if not pdf_path.exists():
        return {"error": "PDF not found"}
    doc = fitz.open(str(pdf_path))
    if page < 0 or page >= len(doc):
        doc.close()
        return {"error": "Page out of range"}
    p = doc[page]
    pix = p.get_pixmap(dpi=150)
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    buf = io.BytesIO()
    img.save(buf, format="WEBP", quality=70)
    doc.close()
    return StreamingResponse(io.BytesIO(buf.getvalue()), media_type="image/webp")


@app.get("/api/pdf_info/{job_id}")
async def pdf_info(job_id: str):
    pdf_path = UPLOADS / f"{job_id}.pdf"
    if not pdf_path.exists():
        return {"error": "PDF not found"}
    doc = fitz.open(str(pdf_path))
    info = {"pages": len(doc), "metadata": doc.metadata}
    doc.close()
    return info


@app.get("/download/{job_id}")
async def download(job_id: str):
    out_dir = OUTPUTS / job_id
    mds = list(out_dir.glob("*.md")) if out_dir.exists() else []
    if not mds:
        return {"error": "Markdown not found"}
    return FileResponse(mds[0], media_type="text/markdown", filename=mds[0].name)


@app.get("/crops/{job_id}/{filename}")
async def serve_crop(job_id: str, filename: str):
    fpath = CROPS / job_id / filename
    if not fpath.exists():
        return {"error": "Crop not found"}
    return FileResponse(fpath, media_type="image/jpeg")


@app.get("/api/telemetry/{job_id}")
async def telemetry(job_id: str):
    if job_id not in sessions:
        return {"error": "Job not found"}
    return sessions[job_id].get("telemetry", {})


# ═══════════════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn
    if not LUNA_KEY:
        print("⚠️  OPENCODE_API_KEY not set in .env file!")
        print("   Get your key at: https://opencode.ai/auth")
        print("   Then add: OPENCODE_API_KEY=your-key-here to .env")
        print()
    uvicorn.run(app, host="0.0.0.0", port=8765)
