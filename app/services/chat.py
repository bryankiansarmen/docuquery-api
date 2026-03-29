from app.db.mongo import chat_history_collection
from datetime import datetime, timezone

async def get_chat_history(document_id: str, session_id: str, limit: int = 10):
    cursor = chat_history_collection.find(
        {"document_id": document_id, "session_id": session_id},
        sort=[("timestamp", -1)],
        limit=limit
    )
    turns = await cursor.to_list(length=limit)
    return list(reversed(turns))

async def save_chat_turn(document_id: str, session_id: str, question: str, answer: str):
    await chat_history_collection.insert_one({
        "document_id": document_id,
        "session_id": session_id,
        "question": question,
        "answer": answer,
        "timestamp": datetime.now(timezone.utc)
    })