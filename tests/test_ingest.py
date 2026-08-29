from pathlib import Path

from services.ingest import ingest_pdf

FIXTURE = Path(__file__).parent / "fixtures" / "sample.pdf"


def test_ingest_pdf_returns_chunks_covering_full_text():
    chunks = ingest_pdf(FIXTURE, chunk_size=500, overlap=50)

    assert len(chunks) == 1
    assert "DocMind test fixture PDF." in chunks[0]
    assert "proves pypdf extraction works end to end" in chunks[0]


def test_ingest_pdf_splits_into_multiple_chunks_with_small_chunk_size():
    chunks = ingest_pdf(FIXTURE, chunk_size=20, overlap=5)

    assert len(chunks) > 1
    # every chunk should still trace back to the original document text
    reassembled = chunks[0] + "".join(c[5:] for c in chunks[1:])
    assert "DocMind" in reassembled
