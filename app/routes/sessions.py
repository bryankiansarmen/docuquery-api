from fastapi import APIRouter, Depends, HTTPException, Query
from app.services.chat import list_chat_sessions, get_session_messages
from app.services.document import get_document_metadata
from app.dependencies import verify_api_key, get_tenant_id
from app.rate_limit import rate_limit

router = APIRouter()


@router.get("/sessions", dependencies=[Depends(verify_api_key), Depends(rate_limit(60, 60))])
async def sessions_list(
    document_id: str,
    tenant_id: str = Depends(get_tenant_id),
    limit: int = Query(50, ge=1, le=200),
):
    metadata = await get_document_metadata(document_id, tenant_id=tenant_id)
    if not metadata:
        raise HTTPException(status_code=404, detail="Document not found")
    file_name = metadata.get("file_name")
    sessions = await list_chat_sessions(file_name, limit=limit)
    return {"document_id": document_id, "sessions": sessions}


@router.get("/sessions/{session_id}", dependencies=[Depends(verify_api_key), Depends(rate_limit(60, 60))])
async def session_detail(
    session_id: str,
    document_id: str,
    tenant_id: str = Depends(get_tenant_id),
):
    metadata = await get_document_metadata(document_id, tenant_id=tenant_id)
    if not metadata:
        raise HTTPException(status_code=404, detail="Document not found")
    file_name = metadata.get("file_name")
    messages = await get_session_messages(file_name, session_id)
    return {"session_id": session_id, "document_id": document_id, "messages": messages}
