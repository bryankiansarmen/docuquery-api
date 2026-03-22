from fastapi import APIRouter, UploadFile, HTTPException
from app.services.pdf import extract_text_from_pdf, chunk_text
from app.services.vector import store_chunks
from app.services.store import DOCUMENT_STORE
from app.services.gemini import client
from loguru import logger

router = APIRouter()

@router.post("/upload")
async def upload_document(file: UploadFile):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    content, page_count = extract_text_from_pdf(await file.read())

    # Chunk the text
    chunks = chunk_text(content)
    
    # Store in ChromaDB
    try:
        store_chunks(chunks, file.filename, client)
        logger.info(f"Stored {len(chunks)} chunks for {file.filename}")
    except Exception as e:
        logger.error(f"Failed to store chunks: {e}")
    
    DOCUMENT_STORE["filename"] = file.filename

    return {"message": "Document uploaded and processed successfully", "pages": page_count, "chunks": len(chunks)}
