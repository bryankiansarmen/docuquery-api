from loguru import logger
from app.db.mongo import document_metadata_collection, document_metadata_collection_sync
from app.models.schemas import DocumentMetadata

async def save_document_metadata(metadata: DocumentMetadata) -> bool:
    if document_metadata_collection is None:
        logger.warning("MongoDB unavailable, skipping metadata save")
        return False

    try:
        query = {"document_id": metadata.document_id}
        if metadata.user_id:
            query["user_id"] = metadata.user_id
        await document_metadata_collection.update_one(
            query,
            {"$set": metadata.model_dump()},
            upsert=True
        )
        logger.info(f"Save metadata for document: {metadata.file_name}")
        return True
    except Exception as e:
        logger.error(f"Failed to save metadata: {e}")
        return False

async def get_document_metadata(document_id: str, tenant_id: str | None = None) -> dict | None:
    if document_metadata_collection is None:
        logger.warning("MongoDB unavailable, skipping metadata retrieval")
        return None

    try:
        query = {"document_id": document_id}
        if tenant_id:
            query["user_id"] = tenant_id
        metadata = await document_metadata_collection.find_one(
            query,
            {"_id": 0}
        )
        return metadata
    except Exception as e:
        logger.error(f"Failed to retrieve metadata: {e}")
        return None

async def get_all_document_metadata(
    tenant_id: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict]:
    if document_metadata_collection is None:
        logger.warning("MongoDB unavailable, skipping metadata retrieval")
        return []

    try:
        query = {}
        if tenant_id:
            query["user_id"] = tenant_id
        cursor = document_metadata_collection.find(
            query,
            {"_id": 0}
        ).sort("uploaded_at", -1)
        if offset:
            cursor = cursor.skip(offset)
        if limit:
            cursor = cursor.limit(limit)
        metadata_list = await cursor.to_list(length=limit or 100)
        return metadata_list
    except Exception as e:
        logger.error(f"Failed to retrieve metadata: {e}")
        return []

def save_document_metadata_sync(metadata: DocumentMetadata) -> bool:
    if document_metadata_collection_sync is None:
        logger.warning("MongoDB sync collection unavailable, skipping metadata save")
        return False

    try:
        query = {"document_id": metadata.document_id}
        if metadata.user_id:
            query["user_id"] = metadata.user_id
        document_metadata_collection_sync.update_one(
            query,
            {"$set": metadata.model_dump()},
            upsert=True
        )
        logger.info(f"Save metadata (sync) for document: {metadata.file_name}")
        return True
    except Exception as e:
        logger.error(f"Failed to save metadata (sync): {e}")
        return False
