import pymupdf

def extract_text_from_pdf(file_stream: bytes) -> tuple[str, int]:
    doc = pymupdf.open(stream=file_stream, filetype="pdf")
    
    all_text = ""
    for page in doc:
        all_text += page.get_text()
    
    page_count = len(doc)
    doc.close()
    
    return all_text, page_count

def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[dict]:
    words = text.split()
    chunks = []
    i = 0
    while i < len(words):
        chunk = " ".join(words[i:i + chunk_size])
        chunks.append({"index": len(chunks), "text": chunk})
        i += chunk_size - overlap
    return chunks