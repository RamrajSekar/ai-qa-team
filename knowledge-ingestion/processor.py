"""Fixed local decoder entry point. Run only in a qualified, network-disabled container.

The API never imports PDF parsers or runs this program. All external commands use
fixed argument lists; no URLs, shells, model instructions or executable input.
"""
import json
import sys
import os
import threading
import time
import signal
from pathlib import Path
from uuid import uuid4


def decode(config):
    root = Path(config["workspace"]).resolve()
    source = root / "input"
    kind = config["format"]
    if source.stat().st_size > config["max_bytes"]: raise ValueError("SIZE_LIMIT")
    result = {"pages": [], "images": []}
    if kind == "txt":
        data = source.read_bytes()
        if len(data) > 240000 or b"\x00" in data: raise ValueError("INVALID_TEXT")
        text = data.decode("utf-8-sig")
        if not text.strip() or len(text) > 60000: raise ValueError("TEXT_LIMIT")
        result["pages"] = [{"page": 1, "text": text}]
    elif kind == "pdf":
        if source.read_bytes()[:5] != b"%PDF-": raise ValueError("INVALID_PDF")
        from pypdf import PdfReader
        reader = PdfReader(source, strict=True)
        if reader.is_encrypted or len(reader.pages) > config["max_pages"]: raise ValueError("PDF_LIMIT")
        total = 0
        for number, page in enumerate(reader.pages, 1):
            text = page.extract_text() or ""; total += len(text)
            if total > 60000: raise ValueError("TEXT_LIMIT")
            result["pages"].append({"page": number, "text": text})
            if config["interpret_images"]:
                from PIL import Image
                Image.MAX_IMAGE_PIXELS = 16000000
                for image in page.images:
                    if len(result["images"]) >= config["max_images"]: break
                    bitmap = image.image
                    if bitmap.width * bitmap.height > 16000000: raise ValueError("IMAGE_LIMIT")
                    bitmap.thumbnail((1024, 1024)); name = uuid4().hex
                    clean = Image.new("RGB", bitmap.size)
                    clean.paste(bitmap.convert("RGB"))
                    clean.save(root / (name + ".png"))
                    result["images"].append({"image_id": name, "page": number})
    elif kind == "docx":
        # Native pagination is not reliable without a renderer: cite paragraph blocks.
        import zipfile
        import xml.etree.ElementTree as ET
        with zipfile.ZipFile(source) as archive:
            entries = archive.infolist()
            if len(entries) > 500 or sum(item.file_size for item in entries) > 20000000: raise ValueError("DOCUMENT_LIMIT")
            if any(item.file_size > max(item.compress_size, 1)*100 for item in entries): raise ValueError("DOCUMENT_LIMIT")
            xml = archive.read("word/document.xml")
            if b"<!DOCTYPE" in xml.upper() or b"<!ENTITY" in xml.upper(): raise ValueError("INVALID_XML")
            element = ET.fromstring(xml)
            ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
            blocks = ["".join(p.itertext()) for p in element.findall(".//w:p", ns)]
            if len(blocks) > 500 or sum(map(len, blocks)) > 60000: raise ValueError("TEXT_LIMIT")
            result["pages"] = [{"block": index, "text": text} for index, text in enumerate(blocks, 1) if text.strip()]
            if config["interpret_images"]: raise ValueError("DOCX_IMAGES_REQUIRE_PDF_EXPORT")
    else:
        raise ValueError("UNSUPPORTED_FORMAT")
    return result


if __name__ == "__main__":
    try:
        config = json.load(sys.stdin)
        if os.name == "posix":
            import resource
            resource.setrlimit(resource.RLIMIT_CPU, (120,120))
            resource.setrlimit(resource.RLIMIT_FSIZE, (32000000,32000000))
            resource.setrlimit(resource.RLIMIT_NOFILE, (128,128))
            resource.setrlimit(resource.RLIMIT_CORE, (0,0))
            supervisor = os.getppid()
            def watchdog():
                deadline = time.monotonic()+300
                while os.getppid() == supervisor and time.monotonic()<deadline: time.sleep(0.25)
                os.killpg(os.getpgrp(),signal.SIGKILL)
            threading.Thread(target=watchdog,daemon=True).start()
        result = decode(config)
        print(json.dumps(result))
    except Exception:
        # Never expose native stderr, parser text, filenames or paths to API/UI.
        print(json.dumps({"error_code": "DECODING_FAILED"}))
        sys.exit(1)
