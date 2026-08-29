import pytest

from services.chunker import chunk_text


def test_chunk_text_splits_with_overlap():
    text = "0123456789" * 100  # 1000 chars

    chunks = chunk_text(text, chunk_size=500, overlap=50)

    assert len(chunks) == 3
    assert chunks[0] == text[0:500]
    assert chunks[1] == text[450:950]
    assert chunks[2] == text[900:1000]


def test_consecutive_chunks_share_overlap_region():
    text = "0123456789" * 100
    chunks = chunk_text(text, chunk_size=500, overlap=50)

    end_of_first = chunks[0][-50:]
    start_of_second = chunks[1][:50]
    assert end_of_first == start_of_second


def test_empty_text_returns_no_chunks():
    assert chunk_text("", chunk_size=500, overlap=50) == []


def test_text_shorter_than_chunk_size_returns_single_chunk():
    text = "short document"
    assert chunk_text(text, chunk_size=500, overlap=50) == [text]


def test_overlap_must_be_smaller_than_chunk_size():
    with pytest.raises(ValueError):
        chunk_text("some text", chunk_size=100, overlap=100)
