import os
from dotenv import load_dotenv
from loguru import logger
import chromadb
from chromadb import Schema, VectorIndexConfig, SparseVectorIndexConfig, K
from chromadb.utils.embedding_functions import (
    ChromaCloudQwenEmbeddingFunction,
    ChromaCloudQwenEmbeddingModel,
    ChromaCloudSpladeEmbeddingFunction,
)

load_dotenv()

CHROMA_HOST = os.getenv("CHROMA_HOST", "api.trychroma.com")
CHROMA_PORT = int(os.getenv("CHROMA_PORT", "443"))
CHROMA_API_KEY = os.getenv("CHROMA_API_KEY")
CHROMA_TENANT = os.getenv("CHROMA_TENANT")
CHROMA_DATABASE = os.getenv("CHROMA_DATABASE", "docuquery")

DEFAULT_TENANT = "default"
SPARSE_INDEX_KEY = "sparse_embedding"

chroma_client = None
document_collection = None
semantic_cache_collection = None

_schema = None
# Cache resolved (per-tenant) collections to avoid repeated network round-trips.
_collection_cache = {}


def build_schema() -> Schema | None:
    """Build a collection Schema with dense (Qwen) and sparse (Splade) embeddings.

    Embeddings are generated server-side by Chroma Cloud when records are added,
    so callers only need to supply ids, documents and metadatas.
    """
    global _schema
    if _schema is not None:
        return _schema

    try:
        dense_ef = ChromaCloudQwenEmbeddingFunction(
            model=ChromaCloudQwenEmbeddingModel.QWEN3_EMBEDDING_0p6B,
            task=None,
        )
        sparse_ef = ChromaCloudSpladeEmbeddingFunction()

        _schema = (
            Schema()
            .create_index(
                config=VectorIndexConfig(space="cosine", embedding_function=dense_ef)
            )
            .create_index(
                config=SparseVectorIndexConfig(
                    source_key=K.DOCUMENT, embedding_function=sparse_ef
                ),
                key=SPARSE_INDEX_KEY,
            )
        )
        logger.info("Built Chroma Cloud schema (dense + sparse indexes)")
        return _schema
    except Exception as e:
        logger.error(f"Failed to build Chroma schema: {e}")
        return None


def collection_name(kind: str, tenant_id: str | None = None) -> str:
    """Shard mutually exclusive data across collections per tenant/org."""
    tenant = tenant_id or DEFAULT_TENANT
    return f"{kind}_{tenant}"


def get_collection(name: str):
    """Fetch a collection by resolved name, caching it per tenant."""
    if not chroma_client:
        return None
    if name not in _collection_cache:
        _collection_cache[name] = chroma_client.get_or_create_collection(
            name=name, schema=build_schema()
        )
    return _collection_cache[name]


def get_document_collection(tenant_id: str | None = None):
    return get_collection(collection_name("documents", tenant_id))


def get_semantic_cache_collection(tenant_id: str | None = None):
    return get_collection(collection_name("semantic_cache", tenant_id))


try:
    if not CHROMA_API_KEY:
        raise ValueError("CHROMA_API_KEY is not set")
    chroma_client = chromadb.CloudClient(
        tenant=CHROMA_TENANT,
        database=CHROMA_DATABASE,
        api_key=CHROMA_API_KEY,
        cloud_host=CHROMA_HOST,
        cloud_port=CHROMA_PORT,
    )
    schema = build_schema()
    if schema is not None:
        document_collection = get_document_collection()
        semantic_cache_collection = get_semantic_cache_collection()
    logger.info(
        f"Connected to Chroma Cloud at {CHROMA_HOST} "
        f"(tenant={CHROMA_TENANT}, database={CHROMA_DATABASE})"
    )
except Exception as e:
    logger.error(f"Failed to connect to Chroma Cloud: {e}")