import chromadb
from loguru import logger
import os

CHROMA_HOST = os.getenv("CHROMA_HOST", "chromadb")
CHROMA_PORT = int(os.getenv("CHROMA_PORT", "8000"))

chroma_client = None
document_collection = None
semantic_cache_collection = None

try:
    if not CHROMA_HOST:
        raise ValueError("CHROMA_HOST is not set")
    chroma_client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
    document_collection = chroma_client.get_or_create_collection("documents")
    semantic_cache_collection = chroma_client.get_or_create_collection("semantic_cache")
    logger.info(f"Connected to ChromaDB at {CHROMA_HOST}:{CHROMA_PORT}")
except Exception as e:
    logger.error(f"Failed to connect to ChromaDB: {e}")