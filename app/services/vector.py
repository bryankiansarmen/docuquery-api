from loguru import logger
from app.db.chroma import document_collection, semantic_cache_collection
import hashlib

def store_document_chunks(chunks: list[dict], file_name: str, client, document_id: str = None):
    if not document_collection:
        logger.error("ChromaDB not available, skipping storage.")
        return
    
    for chunk in chunks:
        try:
            result = client.models.embed_content(
            model="gemini-embedding-001",
                contents=chunk["text"]
            )
            prefix = document_id if document_id else file_name
            document_collection.add(
                ids=[f"{prefix}-{chunk['index']}"],
                embeddings=[result.embeddings[0].values],
                documents=[chunk["text"]],
                metadatas=[{"source": file_name, "index": chunk["index"]}]
            )
        except Exception as e:
            logger.error(f"Error storing chunk {chunk['index']}: {e}")

def search_document_chunks(question: str, client, n=5) -> list[str]:
    if not document_collection:
        logger.error("ChromaDB not available, skipping search.")
        return []

    try:
        result = client.models.embed_content(
        model="gemini-embedding-001",
            contents=question
        )
        results = document_collection.query(
            query_embeddings=[result.embeddings[0].values],
            n_results=n
        )
        return results["documents"][0] if results["documents"] else []
    except Exception as e:
        logger.error(f"Error searching chunks: {e}")
        return []

def get_semantic_question_cache(question: str, file_name: str, client, threshold=0.3) -> dict | None:
    if not semantic_cache_collection:
        return None

    try:
        result = client.models.embed_content(
            model="gemini-embedding-001",
            contents=question
        )
        query_embedding = result.embeddings[0].values
        
        results = semantic_cache_collection.query(
            query_embeddings=[query_embedding],
            n_results=1,
            where={"source": file_name}
        )
        
        if results["documents"] and results["distances"] and results["distances"][0][0] < threshold:
            logger.info(f"Semantic cache hit (distance: {results['distances'][0][0]:.4f})")
            return {
                "answer": results["documents"][0][0],
                "metadata": results["metadatas"][0][0]
            }
        return None
    except Exception as e:
        logger.error(f"Error checking semantic cache: {e}")
        return None

def save_semantic_question_cache(question: str, answer: str, file_name: str, client):
    if not semantic_cache_collection:
        return

    try:
        cache_id = hashlib.sha256(f"{question}{file_name}".encode()).hexdigest()
        
        result = client.models.embed_content(
            model="gemini-embedding-001",
            contents=question
        )
        
        semantic_cache_collection.add(
            ids=[cache_id],
            embeddings=[result.embeddings[0].values],
            documents=[answer],
            metadatas=[{"question": question, "source": file_name}]
        )
        logger.info(f"Saved to semantic cache: {question[:50]}...")
    except Exception as e:
        logger.error(f"Error saving to semantic cache: {e}")
