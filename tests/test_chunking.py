import pytest

from rag_qa.chunking import chunk_text


def test_empty_text_returns_no_chunks():
    assert chunk_text("") == []


def test_whitespace_only_text_returns_no_chunks():
    assert chunk_text("   \n\t  ") == []


def test_text_shorter_than_chunk_size_returns_single_chunk():
    text = "這是一段很短的文字。"
    result = chunk_text(text, chunk_size=500, overlap=50)
    assert result == [text]


def test_text_longer_than_chunk_size_splits_into_multiple_chunks():
    text = "A" * 1200
    result = chunk_text(text, chunk_size=500, overlap=50)
    assert len(result) > 1
    assert all(len(chunk) <= 500 for chunk in result)


def test_consecutive_chunks_overlap_by_configured_amount():
    text = "".join(str(i % 10) for i in range(1200))
    chunk_size, overlap = 500, 50
    result = chunk_text(text, chunk_size=chunk_size, overlap=overlap)

    for i in range(len(result) - 1):
        tail_of_current = result[i][-overlap:]
        head_of_next = result[i + 1][:overlap]
        assert tail_of_current == head_of_next


def test_chunks_reconstruct_full_text_without_gaps():
    text = "".join(str(i % 10) for i in range(1200))
    chunk_size, overlap = 500, 50
    result = chunk_text(text, chunk_size=chunk_size, overlap=overlap)

    stride = chunk_size - overlap
    reconstructed = result[0]
    for chunk in result[1:]:
        reconstructed += chunk[overlap:]
    assert reconstructed == text
    assert stride > 0


def test_overlap_must_be_smaller_than_chunk_size():
    with pytest.raises(ValueError):
        chunk_text("some text", chunk_size=100, overlap=100)


def test_overlap_cannot_be_negative():
    with pytest.raises(ValueError):
        chunk_text("some text", chunk_size=100, overlap=-1)
