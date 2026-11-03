"""Pull plain text out of uploaded .pdf / .txt files."""
from __future__ import annotations

import io
from pathlib import PurePath

from pypdf import PdfReader

SUPPORTED_EXTENSIONS = {".pdf", ".txt"}


class UnsupportedFileError(ValueError):
    pass


def get_extension(filename: str) -> str:
    return PurePath(filename).suffix.lower()


def extract_text(filename: str, content: bytes) -> str:
    ext = get_extension(filename)
    if ext == ".txt":
        return content.decode("utf-8", errors="ignore")
    if ext == ".pdf":
        reader = PdfReader(io.BytesIO(content))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    raise UnsupportedFileError(f"Unsupported file type '{ext}'. Use .pdf or .txt")
