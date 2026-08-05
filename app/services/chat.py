from app.db.mongo import chat_history_collection
from datetime import datetime, timezone

async def list_chat_sessions(document_id: str, limit: int = 50) -> list[dict]:
    """List distinct chat sessions for a document, newest first."""
    if chat_history_collection is None:
        return []

    pipeline = [
        {"$match": {"document_id": document_id}},
        {"$sort": {"timestamp": -1}},
        {
            "$group": {
                "_id": "$session_id",
                "title": {"$first": "$question"},
                "message_count": {"$sum": 1},
                "updated_at": {"$first": "$timestamp"},
            }
        },
        {"$sort": {"updated_at": -1}},
        {"$limit": limit},
    ]

    cursor = chat_history_collection.aggregate(pipeline)
    raw = await cursor.to_list(length=limit)

    def _iso(value):
        if value is None:
            return None
        if isinstance(value, datetime):
            return value.isoformat()
        return str(value)

    return [
        {
            "session_id": item["_id"],
            "title": (item.get("title") or "").strip()[:120],
            "message_count": item.get("message_count", 0),
            "updated_at": _iso(item.get("updated_at")),
        }
        for item in raw
    ]


async def get_session_messages(document_id: str, session_id: str) -> list[dict]:
    """Return the full question/answer sequence for a session, oldest first."""
    if chat_history_collection is None:
        return []

    cursor = chat_history_collection.find(
        {"document_id": document_id, "session_id": session_id},
        sort=[("timestamp", 1)],
    )
    turns = await cursor.to_list(length=None)

    messages: list[dict] = []
    for turn in turns:
        if turn.get("question"):
            messages.append({"role": "user", "content": turn["question"]})
        if turn.get("answer"):
            messages.append({"role": "assistant", "content": turn["answer"]})
    return messages


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