from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from core.errors import InvalidPDFError


def extract_text(pdf_path: str | Path) -> str:
    try:
        reader = PdfReader(pdf_path)
        pages_text = [page.extract_text() or "" for page in reader.pages]
    except PdfReadError as exc:
        raise InvalidPDFError(f"Could not read PDF: {pdf_path}") from exc
    return "\n".join(pages_text)
