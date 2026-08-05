DEFAULT_TENANT = "default"

# In-memory document store, keyed per tenant to avoid cross-tenant bleed.
DOCUMENT_STORE = {}


def _default_state() -> dict:
    return {
        "file_name": None,
        "document_id": None,
        "page_count": None,
        "chunk_count": None,
        "content": None,
    }


def get_store(tenant_id: str | None = None) -> dict:
    key = tenant_id or DEFAULT_TENANT
    if key not in DOCUMENT_STORE:
        DOCUMENT_STORE[key] = _default_state()
    return DOCUMENT_STORE[key]
