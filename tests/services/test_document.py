from app.services.document import save_document_metadata, get_document_metadata, get_all_document_metadata
from app.models.schemas import DocumentMetadata
from unittest.mock import MagicMock, AsyncMock

async def test_save_document_metadata(mock_mongo):
    metadata = DocumentMetadata(
        document_id="doc123",
        file_name="test.pdf",
        chunk_count=10,
        page_count=2
    )
    
    await save_document_metadata(metadata)
    
    mock_mongo["document"].update_one.assert_called_once()
    args, kwargs = mock_mongo["document"].update_one.call_args
    assert args[0] == {"document_id": "doc123"}
    assert "$set" in args[1]

async def test_get_document_metadata(mock_mongo):
    mock_mongo["document"].find_one.return_value = {"document_id": "doc123", "file_name": "test.pdf"}
    
    result = await get_document_metadata("doc123")
    
    assert result["document_id"] == "doc123"
    mock_mongo["document"].find_one.assert_called_once_with({"document_id": "doc123"}, {"_id": 0})

async def test_get_all_document_metadata(mock_mongo):
    mock_cursor = MagicMock()
    mock_cursor.sort.return_value = mock_cursor
    mock_cursor.to_list = AsyncMock(return_value=[{"document_id": "doc123"}])
    mock_mongo["document"].find.return_value = mock_cursor
    
    result = await get_all_document_metadata()
    
    assert len(result) == 1
    assert result[0]["document_id"] == "doc123"
