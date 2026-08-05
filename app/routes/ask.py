import asyncio, uuid
from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone
from app.models.schemas import Question
from app.services.store import get_store
from app.clients.openrouter import get_chat_client
from app.services.llm import generate_answer
from app.services.vector import search_document_chunks, get_semantic_question_cache, save_semantic_question_cache
from app.services.cache import create_answer_key, get_answer_cache, save_answer_cache, get_active_document
from app.services.chat import get_chat_history, save_chat_turn
from app.services.document import get_document_metadata
from app.dependencies import verify_api_key, get_tenant_id
from app.rate_limit import rate_limit
from loguru import logger

router = APIRouter()


@router.post("/ask", dependencies=[Depends(verify_api_key), Depends(rate_limit(30, 60))])
async def ask_question(question: Question, tenant_id: str = Depends(get_tenant_id)):
    store = get_store(tenant_id)
    document_id = question.document_id
    file_name = None

    # Resolve the target document. An explicit document_id that cannot be found
    # is an error (never silently fall back to a different, "active" document).
    if document_id and store.get("document_id") == document_id:
        file_name = store.get("file_name")
    elif document_id:
        metadata = await get_document_metadata(document_id, tenant_id=tenant_id)
        if metadata:
            file_name = metadata.get("file_name")
            store.update({
                "file_name": file_name,
                "document_id": metadata.get("document_id") or document_id,
                "page_count": metadata.get("page_count"),
                "chunk_count": metadata.get("chunk_count"),
                "content": None,
            })
        else:
            raise HTTPException(status_code=400, detail="Document not found. Please upload the document first.")
    else:
        # No document id supplied: recover the most recently processed document.
        active_document = await asyncio.to_thread(get_active_document, tenant_id)
        if active_document:
            store.update(active_document)
            file_name = store.get("file_name")
            document_id = store.get("document_id")
            logger.info(f"Recovered active document from Redis: {file_name}")

    if not file_name:
        raise HTTPException(status_code=400, detail="No document uploaded yet. Please upload a PDF first.")

    session_id = question.session_id or str(uuid.uuid4())

    # Check exact cache first.
    cache_key = create_answer_key(question.message, file_name, tenant_id)
    cached_answer = await asyncio.to_thread(get_answer_cache, cache_key)
    if cached_answer:
        logger.info(f"Exact cache hit: {question.message}")
        await save_chat_turn(file_name, session_id, question.message, cached_answer)
        return {
            "answer": cached_answer,
            "session_id": session_id,
            "source_file": file_name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "cache_type": "exact",
        }

    # Check semantic cache.
    semantic_question_cached = await asyncio.to_thread(
        get_semantic_question_cache, question.message, file_name, tenant_id
    )
    if semantic_question_cached:
        logger.info(f"Semantic question cache hit: {question.message}")
        await save_chat_turn(file_name, session_id, question.message, semantic_question_cached["answer"])
        return {
            "answer": semantic_question_cached["answer"],
            "session_id": session_id,
            "source_file": semantic_question_cached["metadata"]["source"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "cache_type": "semantic_question",
        }

    logger.info(f"Processing question: {question.message}")

    try:
        history = await get_chat_history(file_name, session_id)

        chunks = await asyncio.to_thread(
            search_document_chunks,
            question.message,
            tenant_id=tenant_id,
            n=5,
            document_id=document_id,
        )
        if not chunks:
            logger.warning("No chunks retrieved for question")

        answer = await asyncio.to_thread(generate_answer, question.message, chunks, history, get_chat_client())

        await save_chat_turn(file_name, session_id, question.message, answer)
        await asyncio.to_thread(save_answer_cache, cache_key, answer)
        await asyncio.to_thread(save_semantic_question_cache, question.message, answer, file_name, tenant_id)

        return {
            "answer": answer,
            "session_id": session_id,
            "source_file": file_name,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        # Log the full traceback but never leak internals to the client.
        logger.exception(f"Error processing question: {question.message}")
        raise HTTPException(status_code=500, detail="Internal server error")