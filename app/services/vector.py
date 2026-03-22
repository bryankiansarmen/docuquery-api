import chromadb
from loguru import logger
import os

CHROMA_HOST = os.getenv("CHROMA_HOST")

try:
    chroma = chromadb.HttpClient(host=CHROMA_HOST, port=8000)
    collection = chroma.get_or_create_collection("documents")
except Exception as e:
    logger.error(f"Failed to connect to ChromaDB at {CHROMA_HOST}: {e}")
    chroma = None
    collection = None

def store_chunks(chunks: list[dict], file_name: str, client, doc_id: str = None):
    if not collection:
        logger.error("ChromaDB not available, skipping storage.")
        return
    
    for chunk in chunks:
        try:
            result = client.models.embed_content(
            model="gemini-embedding-001",
                contents=chunk["text"]
            )
            prefix = doc_id if doc_id else file_name
            collection.add(
                ids=[f"{prefix}-{chunk['index']}"],
                embeddings=[result.embeddings[0].values],
                documents=[chunk["text"]],
                metadatas=[{"source": file_name, "index": chunk["index"]}]
            )
        except Exception as e:
            logger.error(f"Error storing chunk {chunk['index']}: {e}")

def search_chunks(question: str, client, n=5) -> list[str]:
    if not collection:
        logger.error("ChromaDB not available, skipping search.")
        return []

    try:
        result = client.models.embed_content(
        model="gemini-embedding-001",
            contents=question
        )
        results = collection.query(
            query_embeddings=[result.embeddings[0].values],
            n_results=n
        )
        return results["documents"][0] if results["documents"] else []
    except Exception as e:
        logger.error(f"Error searching chunks: {e}")
        return []
