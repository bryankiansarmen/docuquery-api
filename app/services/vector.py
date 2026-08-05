from loguru import logger
import hashlib
from chromadb import Search, K, Knn, Rrf
from chromadb.execution.expression.operator import GroupBy, MinK

from app.db.chroma import (
    SPARSE_INDEX_KEY,
    document_collection,
    semantic_cache_collection,
    get_document_collection,
    get_semantic_cache_collection,
)

DENSE_LIMIT = 200
RRF_K = 60
RRF_WEIGHTS = [0.7, 0.3]


def _document_collection(tenant_id: str | None = None):
    # Prefer the caller-provided (sharded) collection, fall back to the default one.
    return get_document_collection(tenant_id) if tenant_id else document_collection


def _semantic_cache_collection(tenant_id: str | None = None):
    return get_semantic_cache_collection(tenant_id) if tenant_id else semantic_cache_collection


def store_document_chunks(
    chunks: list[dict],
    file_name: str,
    document_id: str = None,
    tenant_id: str | None = None,
) -> bool:
    """Index document chunks into the (per-tenant) documents collection.

    Dense embeddings are generated via Chroma Cloud Qwen and sparse embeddings
    via Chroma Cloud Splade automatically from the collection Schema.

    Returns True on success so callers (the worker) can fail the job rather
    than silently reporting a completed document that is not searchable.
    """
    collection = _document_collection(tenant_id)
    if not collection:
        logger.error("ChromaDB not available, skipping storage.")
        return False

    source_id = document_id or file_name
    ids = []
    documents = []
    metadatas = []
    for chunk in chunks:
        chunk_index = chunk["index"]
        ids.append(f"{source_id}-{chunk_index}")
        documents.append(chunk["text"])
        # document_id + chunk_index metadata enable GroupBy deduplication.
        metadatas.append({
            "source": file_name,
            "document_id": source_id,
            "chunk_index": chunk_index,
        })

    try:
        collection.add(ids=ids, documents=documents, metadatas=metadatas)
        logger.info(f"Stored {len(chunks)} chunks for {file_name}")
        return True
    except Exception as e:
        logger.error(f"Error storing chunks: {e}")
        return False


def search_document_chunks(
    question: str,
    tenant_id: str | None = None,
    n: int = 5,
    document_id: str | None = None,
) -> list[str]:
    """Hybrid search (RRF) over dense + sparse embeddings.

    Results are deduplicated across chunks of the same source document using
    GroupBy on the ``document_id`` metadata key (one chunk per document).
    """
    collection = _document_collection(tenant_id)
    if not collection:
        logger.error("ChromaDB not available, skipping search.")
        return []

    try:
        dense_rank = Knn(
            query=question, key=K.EMBEDDING, return_rank=True, limit=DENSE_LIMIT
        )
        sparse_rank = Knn(
            query=question, key=SPARSE_INDEX_KEY, return_rank=True, limit=DENSE_LIMIT
        )
        hybrid_rank = Rrf(
            ranks=[dense_rank, sparse_rank], weights=RRF_WEIGHTS, k=RRF_K
        )

        search = (
            Search()
            .rank(hybrid_rank)
            .group_by(
                GroupBy(
                    keys=K("document_id"),
                    aggregate=MinK(keys=K.SCORE, k=1),
                )
            )
            .limit(n)
            .select(K.DOCUMENT, K.SCORE, "document_id", "chunk_index", "source")
        )
        if document_id:
            search = search.where(K("document_id") == document_id)

        results = collection.search(search)
        rows = results.rows()[0] if getattr(results, "rows", None) and results.rows() else []
        return [row["document"] for row in rows]
    except Exception as e:
        logger.error(f"Error searching chunks: {e}")
        return []


def get_semantic_question_cache(
    question: str,
    file_name: str,
    tenant_id: str | None = None,
    threshold: float = 0.3,
) -> dict | None:
    collection = _semantic_cache_collection(tenant_id)
    if not collection:
        return None

    try:
        search = (
            Search()
            .where(K("source") == file_name)
            .rank(Knn(query=question, key=K.EMBEDDING))
            .limit(1)
            .select(K.DOCUMENT, K.SCORE, "source", "question")
        )

        results = collection.search(search)
        rows = results.rows()[0] if getattr(results, "rows", None) and results.rows() else []
        if not rows:
            return None

        row = rows[0]
        score = row.get("score")
        if score is not None and score < threshold:
            logger.info(f"Semantic cache hit (distance: {score:.4f})")
            return {
                "answer": row.get("document"),
                "metadata": row.get("metadata", {}),
            }
        return None
    except Exception as e:
        logger.error(f"Error checking semantic cache: {e}")
        return None


def save_semantic_question_cache(
    question: str,
    answer: str,
    file_name: str,
    tenant_id: str | None = None,
):
    collection = _semantic_cache_collection(tenant_id)
    if not collection:
        return

    try:
        cache_id = hashlib.sha256(f"{question}{file_name}{tenant_id or ''}".encode()).hexdigest()
        collection.upsert(
            ids=[cache_id],
            documents=[answer],
            metadatas=[{"question": question, "source": file_name}],
        )
        logger.info(f"Saved to semantic cache: {question[:50]}...")
    except Exception as e:
        logger.error(f"Error saving to semantic cache: {e}")