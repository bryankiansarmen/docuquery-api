from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone
from app.models.schemas import Question
from app.services.store import DOCUMENT_STORE
from app.services.gemini import generate_answer, client
from app.services.vector import search_chunks
from app.services.cache import make_key, get_cache, set_cache
from app.dependencies import verify_api_key
from loguru import logger

router = APIRouter()

@router.post("/ask", dependencies=[Depends(verify_api_key)])
async def ask_question(question: Question):
    filename = DOCUMENT_STORE["filename"]
    if not filename:
        raise HTTPException(status_code=400, detail="No document uploaded yet. Please upload a PDF first.")
    
    # Check cache
    cache_key = make_key(question.message, filename)
    cached_response = get_cache(cache_key)
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
            "source_file": filename,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Save to cache
        set_cache(cache_key, response_data)
        
        return response_data
        
    except Exception as e:
        logger.error(f"Error processing question: {e}")
        raise HTTPException(status_code=500, detail=str(e))
