from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone
from app.models.schemas import Question
from app.services.store import DOCUMENT_STORE
from app.services.gemini import generate_answer, client
from app.services.vector import search_chunks
from app.services.cache import create_answer_key, get_answer_cache, save_answer_cache
from app.dependencies import verify_api_key
from loguru import logger

router = APIRouter()

@router.post("/ask", dependencies=[Depends(verify_api_key)])
async def ask_question(question: Question):
    file_name = DOCUMENT_STORE["file_name"]
    if not file_name:
        raise HTTPException(status_code=400, detail="No document uploaded yet. Please upload a PDF first.")
    
    # Check cache
    cache_key = create_answer_key(question.message, file_name)
    cached_response = get_answer_cache(cache_key)
    if cached_response:
        logger.info(f"Cache hit for question: {question.message}")
        return cached_response
    
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
        
        # Save to cache
        save_answer_cache(cache_key, response_data)
        
        return response_data
        
    except Exception as e:
        logger.error(f"Error processing question: {e}")
        raise HTTPException(status_code=500, detail=str(e))
