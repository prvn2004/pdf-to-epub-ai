import os
import re
import io
import shutil
import zipfile
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Tuple
from app.config import settings
from app.services.session_service import session_manager

class EPUBService:
    def generate_epub(self, job_id: str, partial: bool = False) -> Path:
        """
        Generate an EPUB eBook from completed page markdowns and image crops for job_id.
        Supports full and partial eBook generation with embedded figure images.
        """
        out_dir = settings.OUTPUTS_DIR / job_id
        out_dir.mkdir(parents=True, exist_ok=True)
        
        sess = session_manager.get_session(job_id) or {}
        valid_pages = session_manager.get_valid_cached_pages(job_id)
        sorted_pagenos = sorted(valid_pages.keys())

        if not sorted_pagenos:
            raise ValueError("No completed pages available to compile EPUB")

        meta = sess.get("telemetry", {})
        title = meta.get("title") or "Book"
        author = meta.get("author") or "Unknown"
        if partial and sess.get("status") != "done":
            title += " (Partial Preview)"

        safe_title = re.sub(r'[<>:"/\\|?*]', "", title).strip() or "book"
        epub_filename = f"{safe_title}.epub"
        epub_path = out_dir / epub_filename

        # Assemble markdown parts
        md_parts = []
        for pageno in sorted_pagenos:
            p_data = valid_pages[pageno]
            text = p_data.get("text", "").strip()
            md_parts.append(f"## Page {pageno}\n\n{text}")

        full_md = f"# {title}\n\n*{author}*\n\n" + "\n\n".join(md_parts) + "\n"

        # Check if Pandoc CLI is installed on host
        pandoc_bin = shutil.which("pandoc")
        if pandoc_bin:
            try:
                return self._compile_with_pandoc(job_id, full_md, epub_path, title, author)
            except Exception as e:
                print(f"[EPUBService warn] Pandoc execution failed: {e}. Falling back to Python compiler.")

        # Fallback to pure Python EPUB packager
        return self._compile_with_python(job_id, valid_pages, sorted_pagenos, epub_path, title, author)

    def _compile_with_pandoc(self, job_id: str, full_md: str, epub_path: Path, title: str, author: str) -> Path:
        out_dir = settings.OUTPUTS_DIR / job_id
        temp_md = out_dir / "temp_epub_input.md"
        
        # Transform leading /crops/{job_id}/ image paths to relative crops/{job_id}/ for Pandoc filesystem lookup
        pandoc_md = re.sub(rf'!\[([^\]]*)\]\(/crops/{job_id}/([^)]+)\)', rf'![\1](crops/{job_id}/\2)', full_md)
        temp_md.write_text(pandoc_md, encoding="utf-8")

        cmd = [
            "pandoc",
            str(temp_md),
            "-o", str(epub_path),
            "--from", "markdown",
            "--to", "epub3",
            "--metadata", f"title={title}",
            "--metadata", f"author={author}",
            "--resource-path", str(settings.BASE_DIR),
            "--toc"
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, cwd=str(settings.BASE_DIR))
        temp_md.unlink(missing_ok=True)

        if res.returncode == 0 and epub_path.exists():
            return epub_path
        raise RuntimeError(f"Pandoc error ({res.returncode}): {res.stderr}")

    def _compile_with_python(self, job_id: str, valid_pages: dict, sorted_pagenos: list, epub_path: Path, title: str, author: str) -> Path:
        """Pure Python EPUB v3 Packager with full embedded image asset support."""
        buf = io.BytesIO()

        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            # 1. mimetype (MUST be uncompressed per EPUB spec)
            zf.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)

            # 2. META-INF/container.xml
            container_xml = """<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="EPUB/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>"""
            zf.writestr("META-INF/container.xml", container_xml)

            # 3. CSS Stylesheet
            css = """body { font-family: Georgia, serif; line-height: 1.6; padding: 1em; color: #222; }
h1 { font-family: sans-serif; font-size: 1.8em; margin-bottom: 0.5em; text-align: center; }
h2 { font-family: sans-serif; font-size: 1.3em; margin-top: 1.5em; border-bottom: 1px solid #ccc; color: #555; }
p { margin-bottom: 1em; text-indent: 1em; }
figure { margin: 1.5em 0; text-align: center; }
figure img { max-width: 100%; height: auto; border-radius: 4px; box-shadow: 0 1px 4px rgba(0,0,0,0.15); }
figcaption { font-size: 0.85em; color: #666; margin-top: 0.4em; }"""
            zf.writestr("EPUB/stylesheet.css", css)

            manifest_items = []
            spine_items = []
            nav_items = []
            embedded_image_files = set()

            # 4. Process each page into XHTML and extract embedded images
            crops_dir = settings.CROPS_DIR / job_id
            for pageno in sorted_pagenos:
                p_data = valid_pages[pageno]
                text = p_data.get("text", "")
                
                xhtml_body, page_images = self._markdown_to_xhtml(text)

                # Embed images referenced on this page into EPUB zip archive
                for img_info in page_images:
                    fname = img_info["filename"]
                    if fname not in embedded_image_files:
                        embedded_image_files.add(fname)
                        crop_file = crops_dir / fname
                        if crop_file.exists():
                            arc_path = f"EPUB/crops/{fname}"
                            zf.write(crop_file, arc_path)
                            
                            mime_type = "image/png" if fname.lower().endswith(".png") else "image/jpeg"
                            if fname.lower().endswith(".webp"):
                                mime_type = "image/webp"
                            
                            safe_id = re.sub(r'[^a-zA-Z0-9_]', '_', fname)
                            manifest_items.append(
                                f'<item id="img_{safe_id}" href="crops/{fname}" media-type="{mime_type}"/>'
                            )

                page_filename = f"page_{pageno}.xhtml"
                xhtml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" lang="en">
<head>
  <meta charset="UTF-8"/>
  <title>Page {pageno}</title>
  <link rel="stylesheet" type="text/css" href="stylesheet.css"/>
</head>
<body>
  <h2>Page {pageno}</h2>
  {xhtml_body}
</body>
</html>"""
                zf.writestr(f"EPUB/{page_filename}", xhtml_content)

                item_id = f"page_{pageno}"
                manifest_items.append(f'<item id="{item_id}" href="{page_filename}" media-type="application/xhtml+xml"/>')
                spine_items.append(f'<itemref idref="{item_id}"/>')
                nav_items.append(f'<li><a href="{page_filename}">Page {pageno}</a></li>')

            # 5. EPUB/content.opf
            manifest_str = "\n    ".join(manifest_items)
            spine_str = "\n    ".join(spine_items)

            opf = f"""<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="pub-id">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="pub-id">urn:uuid:{job_id}</dc:identifier>
    <dc:title>{title}</dc:title>
    <dc:creator>{author}</dc:creator>
    <dc:language>en</dc:language>
    <meta property="dcterms:modified">2026-08-05T00:00:00Z</meta>
  </metadata>
  <manifest>
    <item id="css" href="stylesheet.css" media-type="text/css"/>
    <item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>
    {manifest_str}
  </manifest>
  <spine>
    {spine_str}
  </spine>
</package>"""
            zf.writestr("EPUB/content.opf", opf)

            # 6. EPUB/nav.xhtml (EPUB 3 Navigation)
            nav_list = "\n        ".join(nav_items)
            nav_xhtml = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" lang="en">
<head><title>Table of Contents</title><link rel="stylesheet" href="stylesheet.css"/></head>
<body>
  <nav epub:type="toc" id="toc">
    <h1>Table of Contents</h1>
    <ol>
        {nav_list}
    </ol>
  </nav>
</body>
</html>"""
            zf.writestr("EPUB/nav.xhtml", nav_xhtml)

        epub_path.write_bytes(buf.getvalue())
        return epub_path

    def _markdown_to_xhtml(self, md: str) -> Tuple[str, List[Dict[str, str]]]:
        """Convert page Markdown to clean XHTML for EPUB and extract embedded image references."""
        if not md:
            return "<p><em>(Empty Page)</em></p>", []
        
        extracted_images = []
        
        # 1. Escape HTML entities
        h = md.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

        # 2. Extract & transform markdown image references: ![alt](src) -> <figure><img src="crops/filename.ext"/></figure>
        def img_replacer(match):
            caption = match.group(1)
            src = match.group(2)
            fname = Path(src).name
            extracted_images.append({
                "filename": fname,
                "original_src": src
            })
            epub_img_src = f"crops/{fname}"
            return f'<figure><img src="{epub_img_src}" alt="{caption}"/><figcaption>{caption}</figcaption></figure>'

        h = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', img_replacer, h)

        # 3. Block formatting
        h = re.sub(r'```([\s\S]*?)```', r'<pre><code>\1</code></pre>', h)
        h = re.sub(r'^###### (.*)$', r'<h6>\1</h6>', h, flags=re.M)
        h = re.sub(r'^##### (.*)$', r'<h5>\1</h5>', h, flags=re.M)
        h = re.sub(r'^#### (.*)$', r'<h4>\1</h4>', h, flags=re.M)
        h = re.sub(r'^### (.*)$', r'<h3>\1</h3>', h, flags=re.M)
        h = re.sub(r'^## (.*)$', r'<h2>\1</h2>', h, flags=re.M)
        h = re.sub(r'^# (.*)$', r'<h1>\1</h1>', h, flags=re.M)
        h = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', h)
        h = re.sub(r'\*([^*\n]+)\*', r'<em>\1</em>', h)

        paragraphs = []
        for block in re.split(r'\n{2,}', h):
            b = block.strip()
            if not b:
                continue
            if re.match(r'^<(h[1-6]|figure|pre|blockquote)', b):
                paragraphs.append(b)
            else:
                paragraphs.append(f"<p>{b.replace('\n', '<br/>')}</p>")

        return "\n".join(paragraphs), extracted_images
