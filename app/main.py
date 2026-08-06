from contextlib import asynccontextmanager
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import upload, ask, documents, sessions
from dotenv import load_dotenv
from loguru import logger
from app.db.mongo import document_metadata_collection, chat_history_collection
from app.services.stream import create_consumer_group

load_dotenv()

CHAT_HISTORY_TTL_DAYS = int(os.getenv("CHAT_HISTORY_TTL_DAYS", "90"))

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        # Create MongoDB indexes
        if document_metadata_collection is not None:
            # Drop the legacy single-field unique index (document_id was globally
            # unique); the same file may now exist per-tenant.
            try:
                await document_metadata_collection.drop_index("document_id_1")
            except Exception:
                pass
            await document_metadata_collection.create_index(
                [("document_id", 1), ("user_id", 1)], unique=True
            )
            await document_metadata_collection.create_index(
                [("uploaded_at", -1)]
            )
            logger.info("Indexes created for document_metadata_collection")

        if chat_history_collection is not None:
            await chat_history_collection.create_index(
                [("document_id", 1), ("session_id", 1), ("timestamp", -1)]
            )
            if CHAT_HISTORY_TTL_DAYS > 0:
                await chat_history_collection.create_index(
                    [("timestamp", 1)], expireAfterSeconds=CHAT_HISTORY_TTL_DAYS * 86400
                )
            logger.info("Indexes created for chat_history_collection")

        # Initialize Redis consumer group
        create_consumer_group()

    except Exception as e:
        logger.error(f"Startup tasks failed: {e}")

    yield
    logger.info("Application cleanup complete")

app = FastAPI(title="DocuQuery API", lifespan=lifespan)

LOG_DIR = os.getenv("LOG_DIR", "/tmp/logs" if os.getenv("RENDER") else "logs")
logger.add(os.path.join(LOG_DIR, "app.log"), rotation="1 day", level="INFO")

CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router)
app.include_router(ask.router)
app.include_router(documents.router)
app.include_router(sessions.router)

@app.get("/health")
async def health_check():
    return {"status": "healthy"}