from fastapi import APIRouter, HTTPException
from datetime import datetime, timezone
from app.models.schemas import Question
from app.services.store import DOCUMENT_STORE
from app.services.gemini import generate_answer

router = APIRouter()

@router.post("/ask")
async def ask_question(question: Question):
    if not DOCUMENT_STORE["content"]:
        raise HTTPException(status_code=400, detail="No document uploaded yet. Please upload a PDF first.")
    
    answer = generate_answer(DOCUMENT_STORE["content"], question.message)

    return {
        "answer": answer,
        "source_file": DOCUMENT_STORE["filename"],
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
