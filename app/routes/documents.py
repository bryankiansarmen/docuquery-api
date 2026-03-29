from fastapi import APIRouter, Depends, HTTPException
from app.services.document import get_all_document_metadata, get_document_metadata
from app.dependencies import verify_api_key

router = APIRouter()

@router.get("/documents", dependencies=[Depends(verify_api_key)])
async def list_documents():
    documents = await get_all_document_metadata()
    return {"documents": documents, "total": len(documents)}

@router.get("/documents/{document_id}", dependencies=[Depends(verify_api_key)])
async def get_document(document_id: str):
    document = await get_document_metadata(document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return document
