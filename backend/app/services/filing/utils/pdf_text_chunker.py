from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TextChunk:
    page_no: int
    chunk_index: int
    text: str


def chunk_text(text: str, chunk_size: int = 700, overlap: int = 100) -> list[str]:
    if not text:
        return []

    chunks: list[str] = []
    start = 0
    text_len = len(text)

    while start < text_len:
        end = min(start + chunk_size, text_len)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= text_len:
            break
        start = max(end - overlap, start + 1)

    return chunks


def build_page_chunks(
    page_no: int, text: str, chunk_size: int = 700, overlap: int = 100
) -> list[TextChunk]:
    raw_chunks = chunk_text(text=text, chunk_size=chunk_size, overlap=overlap)
    return [
        TextChunk(page_no=page_no, chunk_index=idx, text=chunk)
        for idx, chunk in enumerate(raw_chunks)
    ]
