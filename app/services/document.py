from loguru import logger
from app.db.mongo import document_metadata_collection, document_metadata_collection_sync
from app.models.schemas import DocumentMetadata

async def save_document_metadata(metadata: DocumentMetadata):
    if document_metadata_collection is None:
        logger.warning("MongoDB unavailable, skipping metadata save")
        return None
    
    try:
        await document_metadata_collection.update_one(
            {"document_id": metadata.document_id},
            {"$set": metadata.model_dump()},
            upsert=True
        )
        logger.info(f"Save metadata for document: {metadata.file_name}")
    except Exception as e:
        logger.error(f"Failed to save metadata: {e}")

async def get_document_metadata(document_id: str) -> dict | None:
    if document_metadata_collection is None:
        logger.warning("MongoDB unavailable, skipping metadata retrieval")
        return None
    
    try:
        metadata = await document_metadata_collection.find_one(
            {"document_id": document_id}, 
            {"_id": 0}
        )
        return metadata
    except Exception as e:
        logger.error(f"Failed to retrieve metadata: {e}")
        return None

async def get_all_document_metadata() -> list[dict]:
    if document_metadata_collection is None:
        logger.warning("MongoDB unavailable, skipping metadata retrieval")
        return []
    
    try:
        cursor = document_metadata_collection.find(
            {},
            {"_id": 0}
        ).sort("uploaded_at", -1)
        metadata_list = await cursor.to_list(length=100)
        return metadata_list
    except Exception as e:
        logger.error(f"Failed to retrieve metadata: {e}")
        return []

def save_document_metadata_sync(metadata: DocumentMetadata):
    if document_metadata_collection_sync is None:
        logger.warning("MongoDB sync collection unavailable, skipping metadata save")
        return
    
    try:
        document_metadata_collection_sync.update_one(
            {"document_id": metadata.document_id},
            {"$set": metadata.model_dump()},
            upsert=True
        )
        logger.info(f"Save metadata (sync) for document: {metadata.file_name}")
    except Exception as e:
        logger.error(f"Failed to save metadata (sync): {e}")
