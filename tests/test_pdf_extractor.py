from pathlib import Path

import pytest

from services.pdf_extractor import extract_text

FIXTURE = Path(__file__).parent / "fixtures" / "sample.pdf"


def test_extract_text_returns_pdf_content():
    text = extract_text(FIXTURE)

    assert "DocMind test fixture PDF." in text
    assert "proves pypdf extraction works end to end" in text


def test_extract_text_raises_on_missing_file():
    with pytest.raises(FileNotFoundError):
        extract_text(Path("tests/fixtures/does_not_exist.pdf"))
