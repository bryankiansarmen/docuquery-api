from fastapi import APIRouter, Depends, HTTPException
from app.services.document import get_all_document_metadata, get_document_metadata
from app.dependencies import verify_api_key

router = APIRouter()

@router.get("/documents", dependencies=[Depends(verify_api_key)])
async def list_documents():
    docs = await get_all_document_metadata()
    return {"documents": docs, "total": len(docs)}

@router.get("/documents/{document_id}", dependencies=[Depends(verify_api_key)])
async def get_document(document_id: str):
    doc = await get_document_metadata(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc
