import io
import warnings
from dataclasses import dataclass
from typing import Sequence

from pypdf import PdfReader


@dataclass(frozen=True)
class PageText:
    page_number: int
    text: str


@dataclass(frozen=True)
class ChunkInput:
    chunk_index: int
    page_number: int
    text: str


def extract_pages(pdf_bytes: bytes) -> list[PageText]:
    pages: list[PageText] = []
    for page_number, page in enumerate(PdfReader(io.BytesIO(pdf_bytes)).pages, start=1):
        text = (page.extract_text() or "").strip()
        if not text:
            warnings.warn(f"PDF page {page_number} has no extractable text", stacklevel=2)
        pages.append(PageText(page_number, text))
    return pages


def chunk_pages(pages: Sequence[PageText], max_chars: int = 500, overlap_chars: int = 80) -> list[ChunkInput]:
    if max_chars <= 0 or overlap_chars < 0 or overlap_chars >= max_chars:
        raise ValueError("chunk sizes require max_chars > overlap_chars >= 0")
    chunks: list[ChunkInput] = []
    step = max_chars - overlap_chars
    for page in pages:
        text = " ".join(page.text.split())
        for start in range(0, len(text), step):
            value = text[start:start + max_chars].strip()
            if value:
                chunks.append(ChunkInput(len(chunks), page.page_number, value))
            if start + max_chars >= len(text):
                break
    return chunks
