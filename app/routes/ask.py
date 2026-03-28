from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone
from app.models.schemas import Question
from app.services.store import DOCUMENT_STORE
from app.clients.gemini import gemini_client
from app.services.gemini import generate_answer
from app.services.vector import search_document_chunks, get_semantic_question_cache, save_semantic_question_cache
from app.services.cache import create_answer_key, get_answer_cache, save_answer_cache, get_active_document
from app.services.chat import get_chat_history, save_chat_turn
from app.dependencies import verify_api_key
from loguru import logger
import uuid

router = APIRouter()

@router.post("/ask", dependencies=[Depends(verify_api_key)])
async def ask_question(question: Question):
    # resolve active document
    file_name = DOCUMENT_STORE.get("file_name")
    if not file_name:
        active_document = get_active_document()
        if active_document:
            DOCUMENT_STORE.update(active_document)
            file_name = DOCUMENT_STORE.get("file_name")
            logger.info(f"Recovered active document from Redis: {file_name}")

    if not file_name:
        raise HTTPException(status_code=400, detail="No document uploaded yet. Please upload a PDF first.")

    session_id = question.session_id or str(uuid.uuid4())

    # check exact cache first
    cache_key = create_answer_key(question.message, file_name)
    cached_response = get_answer_cache(cache_key)
    if cached_response:
        logger.info(f"Exact cache hit: {question.message}")
        return cached_response

    # check semantic cache
    semantic_question_cached = get_semantic_question_cache(question.message, file_name, gemini_client)
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

        chunks = search_document_chunks(question.message, gemini_client)
        if not chunks:
            chunks = ["No specific context found in the uploaded document."]

        answer = generate_answer(question.message, chunks, history, gemini_client)

        await save_chat_turn(file_name, session_id, question.message, answer)
        save_answer_cache(cache_key, answer)
        save_semantic_question_cache(question.message, answer, file_name, gemini_client)

        return {
            "answer": answer,
            "session_id": session_id,
            "source_file": file_name,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    except Exception as e:
        logger.error(f"Error processing question: {e}")
        raise HTTPException(status_code=500, detail=str(e))
