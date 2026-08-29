from pathlib import Path

import pytest

from core.errors import InvalidPDFError
from services.pdf_extractor import extract_text

FIXTURE = Path(__file__).parent / "fixtures" / "sample.pdf"


def test_extract_text_returns_pdf_content():
    text = extract_text(FIXTURE)

    assert "Maya Chen" in text
    assert "backend engineer" in text


def test_extract_text_raises_on_missing_file():
    with pytest.raises(FileNotFoundError):
        extract_text(Path("tests/fixtures/does_not_exist.pdf"))


def test_extract_text_raises_invalid_pdf_error_on_corrupt_file(tmp_path):
    garbage = tmp_path / "garbage.pdf"
    garbage.write_text("this is not a pdf")

    with pytest.raises(InvalidPDFError):
        extract_text(garbage)
