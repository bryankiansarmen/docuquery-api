from fastapi import APIRouter, UploadFile, HTTPException
from app.services.pdf import extract_text_from_pdf, chunk_text
from app.services.vector import store_chunks
from app.services.store import DOCUMENT_STORE
from app.services.gemini import client
from app.services.cache import get_doc_meta, save_doc_meta
from loguru import logger
import hashlib

router = APIRouter()

@router.post("/upload")
async def upload_document(file: UploadFile):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    file_bytes = await file.read()
    doc_id = hashlib.sha256(file_bytes).hexdigest()

    # Check for existing document in Redis service
    existing_meta = get_doc_meta(doc_id)
    
    if not existing_meta and DOCUMENT_STORE["doc_id"] == doc_id:
        existing_meta = DOCUMENT_STORE

    if existing_meta:
        return {"message": "Document already processed", "page_count": existing_meta["page_count"]}

    content, page_count = extract_text_from_pdf(file_bytes)

    # Chunk the text
    chunks = chunk_text(content)
    
    # Store in ChromaDB
    try:
        store_chunks(chunks, file.filename, client, doc_id)
        logger.info(f"Stored {len(chunks)} chunks for {file.filename}")
        
        # Update both in-memory and persistent store only on success
        DOCUMENT_STORE["file_name"] = file.filename
        DOCUMENT_STORE["doc_id"] = doc_id
        DOCUMENT_STORE["page_count"] = page_count

        save_doc_meta(doc_id, DOCUMENT_STORE)
        logger.debug(f"Persisted document metadata to Redis: {doc_id}")

    except Exception as e:
        logger.error(f"Failed to store chunks: {e}")
        raise HTTPException(status_code=500, detail="Failed to process document storage")

    return {"message": "Document uploaded and processed successfully", "page_count": page_count, "chunks": len(chunks)}
