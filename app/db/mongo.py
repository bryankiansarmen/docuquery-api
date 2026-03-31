from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient
import os
from loguru import logger

MONGO_URL = os.getenv("MONGO_URL", "mongodb://mongodb:27017")

# Async clients/collections
mongo_client = None
db = None
chat_history_collection = None
document_metadata_collection = None

# Sync clients/collections
mongo_client_sync = None
db_sync = None
chat_history_collection_sync = None
document_metadata_collection_sync = None

try:
    if not MONGO_URL:
        raise ValueError("MONGO_URL is not set")
    
    # Init Async
    mongo_client = AsyncIOMotorClient(MONGO_URL, serverSelectionTimeoutMS=5000)
    db = mongo_client["docuquery"]
    chat_history_collection = db["chat_history"]
    document_metadata_collection = db["document_metadata"]
    
    # Init Sync
    mongo_client_sync = MongoClient(MONGO_URL, serverSelectionTimeoutMS=5000)
    db_sync = mongo_client_sync["docuquery"]
    document_metadata_collection_sync = db_sync["document_metadata"]
    
    logger.info(f"Connected to MongoDB at {MONGO_URL} (Async & Sync)")
except Exception as e:
    logger.error(f"Failed to connect to MongoDB: {e}")