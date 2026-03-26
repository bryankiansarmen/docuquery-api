from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone
from app.models.schemas import Question
from app.services.store import DOCUMENT_STORE
from app.services.gemini import generate_answer, client
from app.services.vector import search_chunks, get_semantic_cache, save_semantic_cache
from app.services.cache import create_answer_key, get_answer_cache, save_answer_cache, get_active_doc
from app.dependencies import verify_api_key
from loguru import logger

router = APIRouter()

@router.post("/ask", dependencies=[Depends(verify_api_key)])
async def ask_question(question: Question):
    file_name = DOCUMENT_STORE.get("file_name")
    
    if not file_name:
        active_doc = get_active_doc()
        if active_doc:
            DOCUMENT_STORE.update(active_doc)
            file_name = DOCUMENT_STORE.get("file_name")
            logger.info(f"Recovered active document from Redis: {file_name}")

    if not file_name:
        raise HTTPException(status_code=400, detail="No document uploaded yet. Please upload a PDF first.")
    
    # Check cache
    cache_key = create_answer_key(question.message, file_name)
    cached_response = get_answer_cache(cache_key)
    if cached_response:
        logger.info(f"Exact cache hit for question: {question.message}")
        return cached_response
    
    # Check semantic cache
    semantic_cached = get_semantic_cache(question.message, file_name, client)
    if semantic_cached:
        logger.info(f"Semantic cache hit for question: {question.message}")
        return {
            "answer": semantic_cached["answer"],
            "source_file": semantic_cached["metadata"]["source"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "cache_type": "semantic"
        }
    
    logger.info(f"Processing question: {question.message}")
    
    try:
        # Semantic search
        relevant_chunks = search_chunks(question.message, client)
        
        if not relevant_chunks:
            relevant_chunks = ["No specific context found in the uploaded document."]
        
        # Generate answer
        answer = generate_answer(question.message, relevant_chunks, client)
        
        response_data = {
            "answer": answer,
            "source_file": file_name,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Save to caches
        save_answer_cache(cache_key, response_data)
        save_semantic_cache(question.message, answer, file_name, client)
        
        return response_data
        
    except Exception as e:
        logger.error(f"Error processing question: {e}")
        raise HTTPException(status_code=500, detail=str(e))
