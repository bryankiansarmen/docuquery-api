from fastapi import FastAPI
from app.routes import upload, ask, documents
from dotenv import load_dotenv
from loguru import logger
from app.db.mongo import document_metadata_collection, chat_history_collection

load_dotenv()

app = FastAPI(title="DocuQuery API")
logger.add("logs/app.log", rotation="1 day", level="INFO")

# Include routers
app.include_router(upload.router)
app.include_router(ask.router)
app.include_router(documents.router)

@app.on_event("startup")
async def create_indexes():
    try:
        if document_metadata_collection is not None:
            await document_metadata_collection.create_index(
                [("document_id", 1)], unique=True, background=True
            )
            await document_metadata_collection.create_index(
                [("uploaded_at", -1)], background=True
            )
            logger.info("Indexes created for document_metadata_collection")

        if chat_history_collection is not None:
            await chat_history_collection.create_index(
                [("document_id", 1), ("session_id", 1), ("timestamp", -1)],
                background=True
            )
            logger.info("Indexes created for chat_history_collection")

    except Exception as e:
        logger.error(f"Failed to create indexes: {e}")