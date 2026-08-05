import os
import importlib
from pathlib import Path
from dotenv import load_dotenv
from loguru import logger
import chromadb
from chromadb import Schema, VectorIndexConfig, SparseVectorIndexConfig, K
from chromadb.utils.embedding_functions import (
    EmbeddingFunction,
    ChromaCloudSpladeEmbeddingFunction,
    register_embedding_function,
)

from app.clients.openrouter import OPENROUTER_EMBEDDING_MODEL, embed_texts

try:
    _schema_utils = importlib.import_module(
        "chromadb.utils.embedding_functions.schemas.schema_utils"
    )
except ImportError:
    _schema_utils = None

load_dotenv()

# The chromadb-client wheel omits the top-level `schemas` package that
# schema_utils.SCHEMAS_DIR points at, breaking Splade config validation with
# FileNotFoundError at collection creation. Point the loader at the schemas
# bundled in this repo when the wheel's schemas are absent.
_CHROMA_SCHEMAS_DIR = Path(__file__).parent / "chroma_schemas"


def resolve_chroma_schemas_dir(real_dir: str, bundled_dir: Path) -> str:
    if Path(real_dir).exists():
        return real_dir
    if bundled_dir.exists():
        return str(bundled_dir)
    return real_dir


if _schema_utils is not None:
    _schema_utils.SCHEMAS_DIR = resolve_chroma_schemas_dir(
        _schema_utils.SCHEMAS_DIR, _CHROMA_SCHEMAS_DIR
    )

CHROMA_HOST = os.getenv("CHROMA_HOST", "api.trychroma.com")
CHROMA_PORT = int(os.getenv("CHROMA_PORT", "443"))
CHROMA_API_KEY = os.getenv("CHROMA_API_KEY")
CHROMA_TENANT = os.getenv("CHROMA_TENANT")
CHROMA_DATABASE = os.getenv("CHROMA_DATABASE", "docuquery")


@register_embedding_function
class OpenRouterBgeM3EmbeddingFunction(EmbeddingFunction[str]):
    """Client-side embedding function backed by OpenRouter's ``baai/bge-m3``.

    The Chroma SDK executes this locally (via the collection's schema) and sends
    the resulting vectors to Chroma Cloud, so no server-side embedding config is
    needed for the dense index.
    """

    def __init__(self, model_name: str | None = None):
        self.model_name = model_name or OPENROUTER_EMBEDDING_MODEL

    def __call__(self, input):
        return embed_texts(list(input), model=self.model_name)

    @staticmethod
    def name() -> str:
        return "openrouter_bge_m3"

    def get_config(self) -> dict:
        return {"model_name": self.model_name}

    @staticmethod
    def build_from_config(config: dict) -> "OpenRouterBgeM3EmbeddingFunction":
        return OpenRouterBgeM3EmbeddingFunction(
            model_name=config.get("model_name", OPENROUTER_EMBEDDING_MODEL)
        )

DEFAULT_TENANT = "default"
SPARSE_INDEX_KEY = "sparse_embedding"

chroma_client = None
document_collection = None
semantic_cache_collection = None

_schema = None
# Cache resolved (per-tenant) collections to avoid repeated network round-trips.
_collection_cache = {}


def build_schema() -> Schema | None:
    """Build a collection Schema with dense (OpenRouter bge-m3) and sparse (Splade) embeddings.

    Dense embeddings are generated client-side via OpenRouter's ``baai/bge-m3``
    endpoint; sparse embeddings are generated server-side by Chroma Cloud Splade.
    """
    global _schema
    if _schema is not None:
        return _schema

    try:
        dense_ef = OpenRouterBgeM3EmbeddingFunction()
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
        logger.info("Built Chroma Cloud schema (OpenRouter bge-m3 dense + Splade sparse indexes)")
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