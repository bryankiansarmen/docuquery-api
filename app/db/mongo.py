from motor.motor_asyncio import AsyncIOMotorClient
import os
from loguru import logger

MONGO_URL = os.getenv("MONGO_URL", "mongodb://mongodb:27017")

mongo_client = None
db = None
chat_history_collection = None
document_metadata_collection = None

try:
    if not MONGO_URL:
        raise ValueError("MONGO_URL is not set")
    mongo_client = AsyncIOMotorClient(MONGO_URL, serverSelectionTimeoutMS=5000)
    db = mongo_client["docuquery"]
    chat_history_collection = db["chat_history"]
    document_metadata_collection = db["document_metadata"]
    logger.info(f"Connected to MongoDB at {MONGO_URL}")
except Exception as e:
    logger.error(f"Failed to connect to MongoDB: {e}")