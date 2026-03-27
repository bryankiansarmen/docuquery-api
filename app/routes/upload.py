from fastapi import APIRouter, UploadFile, HTTPException
from app.services.pdf import extract_text_from_pdf, chunk_text
from app.services.vector import store_document_chunks
from app.services.store import DOCUMENT_STORE
from app.services.gemini import client
from app.services.cache import get_document_metadata, save_document_metadata
from app.dependencies import verify_api_key
from loguru import logger
import hashlib

router = APIRouter()

@router.post("/upload", dependencies=[Depends(verify_api_key)])
async def upload_document(file: UploadFile):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    file_bytes = await file.read()
    document_id = hashlib.sha256(file_bytes).hexdigest()

    if DOCUMENT_STORE.get("document_id") == document_id:
        logger.info(f"Document already active in memory: {file.filename}")
        return {
            "message": "Document already processed and active",
            "page_count": DOCUMENT_STORE["page_count"],
            "chunks": DOCUMENT_STORE.get("chunk_count")
        }

    existing_metadata = get_document_metadata(document_id)
    if existing_metadata:
        DOCUMENT_STORE.update(existing_metadata)
        logger.info(f"Re-activated existing document from Redis: {existing_metadata['file_name']}")
        return {
            "message": "Document already processed and re-activated",
            "page_count": existing_metadata["page_count"],
            "chunks": existing_metadata.get("chunk_count")
        }

    content, page_count = extract_text_from_pdf(file_bytes)
    chunks = chunk_text(content)

    try:
        store_document_chunks(chunks, file.filename, client, document_id)
        logger.info(f"Stored {len(chunks)} chunks for {file.filename}")

        # persist to in-memory store
        DOCUMENT_STORE.update({
            "file_name": file.filename,
            "doc_id": document_id,
            "page_count": page_count,
            "chunk_count": len(chunks),
            "content": content
        })

        # persist to Redis
        save_document_metadata(document_id, {
            "file_name": file.filename,
            "doc_id": document_id,
            "page_count": page_count,
            "chunk_count": len(chunks)
        })
        logger.debug(f"Persisted document metadata to Redis: {document_id}")

    except Exception as e:
        logger.error(f"Failed to store chunks: {e}")
        raise HTTPException(status_code=500, detail="Failed to process document storage")

    return {
        "message": "Document uploaded and processed successfully",
        "page_count": page_count,
        "chunks": len(chunks)
    }
