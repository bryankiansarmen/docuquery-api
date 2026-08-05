from fastapi import APIRouter, Depends, HTTPException, Query
from app.services.document import get_all_document_metadata, get_document_metadata
from app.dependencies import verify_api_key, get_tenant_id
from app.rate_limit import rate_limit

router = APIRouter()

@router.get("/documents", dependencies=[Depends(verify_api_key), Depends(rate_limit(60, 60))])
async def list_documents(
    tenant_id: str = Depends(get_tenant_id),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    documents = await get_all_document_metadata(tenant_id=tenant_id, limit=limit, offset=offset)
    return {"documents": documents, "total": len(documents)}

@router.get("/documents/{document_id}", dependencies=[Depends(verify_api_key), Depends(rate_limit(60, 60))])
async def get_document(document_id: str, tenant_id: str = Depends(get_tenant_id)):
    document = await get_document_metadata(document_id, tenant_id=tenant_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return document