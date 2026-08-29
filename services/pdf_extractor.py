from pathlib import Path

from pypdf import PdfReader


def extract_text(pdf_path: str | Path) -> str:
    reader = PdfReader(pdf_path)
    pages_text = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(pages_text)
