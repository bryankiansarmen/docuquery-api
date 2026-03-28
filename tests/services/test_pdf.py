from unittest.mock import MagicMock
from app.services.pdf import chunk_text, extract_text_from_pdf

def test_chunk_text():
    # 100 words of repeating text
    text = "word " * 100
    
    chunks = chunk_text(text, chunk_size=20, overlap=5)
    
    assert len(chunks) > 0
    assert isinstance(chunks[0], dict)
    assert "text" in chunks[0]
    assert "index" in chunks[0]
    assert len(chunks[0]["text"].split()) == 20

def test_chunk_text_small_text():
    text = "hello world"
    
    # Large chunk_size, text completely fits
    chunks = chunk_text(text, chunk_size=10, overlap=2)
    
    assert len(chunks) == 1
    assert chunks[0]["text"] == "hello world"
    assert chunks[0]["index"] == 0

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
