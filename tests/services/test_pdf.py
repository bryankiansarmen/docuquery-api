from unittest.mock import MagicMock
from app.services.pdf import chunk_text, extract_text_from_pdf, MAX_CHUNK_BYTES

def test_max_chunk_bytes_within_chroma_limit():
    assert MAX_CHUNK_BYTES <= 16384

def test_chunk_text_small_text():
    text = "hello world"

    chunks = chunk_text(text)

    assert len(chunks) == 1
    assert chunks[0]["text"] == "hello world"
    assert chunks[0]["index"] == 0

def test_chunk_text_line_based():
    text = "line one\nline two\nline three\nline four\nline five\nline six\n"

    chunks = chunk_text(text, max_bytes=40, overlap_lines=0)

    assert len(chunks) > 1
    for chunk in chunks:
        assert isinstance(chunk, dict)
        assert "text" in chunk
        assert "index" in chunk
        assert len(chunk["text"].encode("utf-8")) <= 40

def test_chunk_text_respects_max_bytes():
    text = "a" * 100 + "\n" + "b" * 100 + "\n" + "c" * 100

    chunks = chunk_text(text, max_bytes=50, overlap_lines=0)

    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk["text"].encode("utf-8")) <= 50

def test_chunk_text_splits_long_line():
    text = "word " * 40

    chunks = chunk_text(text, max_bytes=20, overlap_lines=0)

    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk["text"].encode("utf-8")) <= 20

def test_chunk_text_overlap_preserves_context():
    lines = [f"line {i} content" for i in range(20)]
    text = "\n".join(lines)

    chunks = chunk_text(text, max_bytes=80, overlap_lines=2)

    assert len(chunks) >= 2
    for current, following in zip(chunks, chunks[1:]):
        current_tail = current["text"].split("\n")[-2:]
        following_head = following["text"].split("\n")[:2]
        assert following_head == current_tail

def test_chunk_text_empty():
    assert chunk_text("") == []

def test_extract_text_from_pdf(mocker):
    mock_doc = MagicMock()
    mock_page_1 = MagicMock()
    mock_page_1.get_text.return_value = "Page 1 Text. "
    mock_page_2 = MagicMock()
    mock_page_2.get_text.return_value = "Page 2 Text."

    # Mock pymupdf Document iterator behavior and length
    mock_doc.__iter__.return_value = [mock_page_1, mock_page_2]
    mock_doc.__len__.return_value = 2

    mock_pymupdf = mocker.patch("app.services.pdf.pymupdf")
    mock_pymupdf.open.return_value = mock_doc

    text, page_count = extract_text_from_pdf(b"fake-bytes")

    assert text == "Page 1 Text. Page 2 Text."
    assert page_count == 2
    mock_pymupdf.open.assert_called_once_with(stream=b"fake-bytes", filetype="pdf")
    mock_doc.close.assert_called_once()
