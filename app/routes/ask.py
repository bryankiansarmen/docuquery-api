from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone
from app.models.schemas import Question
from app.services.store import DOCUMENT_STORE
from app.clients.openrouter import get_chat_client
from app.services.llm import generate_answer
from app.services.vector import search_document_chunks, get_semantic_question_cache, save_semantic_question_cache
from app.services.cache import create_answer_key, get_answer_cache, save_answer_cache, get_active_document
from app.services.chat import get_chat_history, save_chat_turn
from app.services.document import get_document_metadata
from app.dependencies import verify_api_key, get_tenant_id
from app.rate_limit import rate_limit
from loguru import logger
import uuid

router = APIRouter()

@router.post("/ask", dependencies=[Depends(verify_api_key), Depends(rate_limit(30, 60))])
async def ask_question(question: Question, tenant_id: str = Depends(get_tenant_id)):
    # resolve the target document. Prefer the requested document_id; fall back
    # to the active (most recently used) document when one is available.
    document_id = question.document_id
    file_name = None

    if DOCUMENT_STORE.get("document_id") == document_id and DOCUMENT_STORE.get("file_name"):
        file_name = DOCUMENT_STORE.get("file_name")
    elif document_id:
        metadata = await get_document_metadata(document_id)
        if metadata:
            file_name = metadata.get("file_name")
            DOCUMENT_STORE.update({
                "file_name": file_name,
                "document_id": document_id,
                "page_count": metadata.get("page_count"),
                "chunk_count": metadata.get("chunk_count"),
                "content": None,
            })

    if not file_name:
        active_document = get_active_document()
        if active_document:
            DOCUMENT_STORE.update(active_document)
            file_name = DOCUMENT_STORE.get("file_name")
            document_id = DOCUMENT_STORE.get("document_id")
            logger.info(f"Recovered active document from Redis: {file_name}")

    if not file_name:
        raise HTTPException(status_code=400, detail="No document uploaded yet. Please upload a PDF first.")

    session_id = question.session_id or str(uuid.uuid4())

    # check exact cache first
    cache_key = create_answer_key(question.message, file_name, tenant_id)
    cached_response = get_answer_cache(cache_key)
    if cached_response:
        logger.info(f"Exact cache hit: {question.message}")
        return cached_response

    # check semantic cache
    semantic_question_cached = get_semantic_question_cache(
        question.message, file_name, tenant_id=tenant_id
    )
    if semantic_question_cached:
        logger.info(f"Semantic question cache hit: {question.message}")
        return {
            "answer": semantic_question_cached["answer"],
            "session_id": session_id,
            "source_file": semantic_question_cached["metadata"]["source"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "cache_type": "semantic_question"
        }

    logger.info(f"Processing question: {question.message}")

    try:
        history = await get_chat_history(file_name, session_id)

        chunks = search_document_chunks(
            question.message,
            tenant_id=tenant_id,
            n=5,
            document_id=document_id,
        )
        if not chunks:
            logger.warning("No chunks retrieved for question")

        answer = generate_answer(question.message, chunks, history, get_chat_client())

        await save_chat_turn(file_name, session_id, question.message, answer)
        save_answer_cache(cache_key, answer)
        save_semantic_question_cache(question.message, answer, file_name, tenant_id=tenant_id)

        return {
            "answer": answer,
            "session_id": session_id,
            "source_file": file_name,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    except Exception as e:
        logger.error(f"Error processing question: {e}")
        raise HTTPException(status_code=500, detail=str(e))
