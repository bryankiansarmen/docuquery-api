import pymupdf

def extract_text_from_pdf(file_stream: bytes) -> tuple[str, int]:
    doc = pymupdf.open(stream=file_stream, filetype="pdf")
    
    all_text = ""
    for page in doc:
        all_text += page.get_text()
    
    page_count = len(doc)
    doc.close()
    
    return all_text, page_count
