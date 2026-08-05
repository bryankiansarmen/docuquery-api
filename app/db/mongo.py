import os
from urllib.parse import quote
from dotenv import load_dotenv
from loguru import logger
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient

load_dotenv()

MONGO_URL = os.getenv("MONGO_URL")
MONGO_HOST = os.getenv("MONGO_HOST", "mongodb")
MONGO_PORT = int(os.getenv("MONGO_PORT", "27017"))
MONGO_USERNAME = os.getenv("MONGO_USERNAME")
MONGO_PASSWORD = os.getenv("MONGO_PASSWORD")
MONGO_SRV = os.getenv("MONGO_SRV", "false").lower() in ("1", "true", "yes")
DATABASE_NAME = "docuquery"


def build_mongo_url() -> str:
    """Resolve the MongoDB connection string.

    An explicit, populated ``MONGO_URL`` wins unless it still contains
    placeholders (e.g. ``<db_username>:<db_password>``). Otherwise the URL is
    composed from ``MONGO_HOST``/``MONGO_PORT`` and
    ``MONGO_USERNAME``/``MONGO_PASSWORD``.
    """
    if MONGO_URL is not None and MONGO_URL and "<" not in MONGO_URL:
        return MONGO_URL

    if not MONGO_URL and not (MONGO_USERNAME or MONGO_PASSWORD):
        raise ValueError("MONGO_URL is not set or no credentials provided")

    scheme = "mongodb+srv" if MONGO_SRV else "mongodb"

    auth = ""
    if MONGO_USERNAME or MONGO_PASSWORD:
        user = quote(MONGO_USERNAME or "", safe="")
        password = f":{quote(MONGO_PASSWORD, safe='')}" if MONGO_PASSWORD else ""
        auth = f"{user}{password}@"

    host = MONGO_HOST if MONGO_SRV else f"{MONGO_HOST}:{MONGO_PORT}"
    suffix = "?appName=DocuQuery" if MONGO_SRV else ""
    return f"{scheme}://{auth}{host}/{DATABASE_NAME}{suffix}"


# Async clients/collections
mongo_client = None
db = None
chat_history_collection = None
document_metadata_collection = None

# Sync clients/collections (used by the synchronous worker)
mongo_client_sync = None
db_sync = None
document_metadata_collection_sync = None

try:
    connection_url = build_mongo_url()

    # Init Async
    mongo_client = AsyncIOMotorClient(
        connection_url, serverSelectionTimeoutMS=5000, connectTimeoutMS=5000
    )
    db = mongo_client[DATABASE_NAME]
    chat_history_collection = db["chat_history"]
    document_metadata_collection = db["document_metadata"]

    # Init Sync
    mongo_client_sync = MongoClient(
        connection_url, serverSelectionTimeoutMS=5000, connectTimeoutMS=5000
    )
    db_sync = mongo_client_sync[DATABASE_NAME]
    document_metadata_collection_sync = db_sync["document_metadata"]

    logger.info(f"Connected to MongoDB database '{DATABASE_NAME}' (Async & Sync)")
except Exception as e:
    logger.error(f"Failed to connect to MongoDB: {e}")