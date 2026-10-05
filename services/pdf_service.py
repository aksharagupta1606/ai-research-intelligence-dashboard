from __future__ import annotations

import pymupdf

from config.settings import MAX_UPLOAD_BYTES
from utils.logger import logger
from utils.text_utils import clean_filename


def extract_pdf(file_bytes: bytes, filename: str) -> dict:
    safe_name = clean_filename(filename)
    if len(file_bytes) > MAX_UPLOAD_BYTES:
        raise ValueError(f"PDF is larger than the {MAX_UPLOAD_BYTES // (1024 * 1024)} MB upload limit.")
    if not file_bytes.startswith(b"%PDF"):
        raise ValueError("This file does not appear to be a valid PDF.")
    try:
        with pymupdf.open(stream=file_bytes, filetype="pdf") as document:
            pages = len(document)
            text = "\n".join(page.get_text("text") for page in document).strip()
    except Exception as error:
        logger.warning("PDF extraction failed for an uploaded document.")
        raise ValueError("The PDF could not be opened. It may be corrupted or password protected.") from error
    if not text:
        return {
            "filename": safe_name,
            "text": "",
            "pages": pages,
            "words": 0,
            "warning": "No selectable text was found. This may be a scanned PDF; OCR is required.",
        }
    return {
        "filename": safe_name,
        "text": text,
        "pages": pages,
        "words": len(text.split()),
        "warning": None,
    }