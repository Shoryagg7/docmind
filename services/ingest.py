from pathlib import Path

from services.chunker import chunk_text
from services.pdf_extractor import extract_text


def ingest_pdf(pdf_path: str | Path, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    text = extract_text(pdf_path)
    return chunk_text(text, chunk_size=chunk_size, overlap=overlap)
