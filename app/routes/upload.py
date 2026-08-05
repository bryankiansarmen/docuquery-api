import asyncio, hashlib, os
from fastapi import APIRouter, UploadFile, HTTPException, Depends, Request
from fastapi.responses import JSONResponse
from app.services.stream import publish_upload_job, get_job_status
from app.models.schemas import JobStatus
from app.dependencies import verify_api_key, get_tenant_id
from app.rate_limit import rate_limit
from app.services.store import get_store
from app.services.cache import get_document_metadata as get_redis_metadata

router = APIRouter()

MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", str(25 * 1024 * 1024)))


@router.post("/upload", dependencies=[Depends(verify_api_key), Depends(rate_limit(10, 60))], status_code=202)
async def upload_document(file: UploadFile, request: Request, tenant_id: str = Depends(get_tenant_id)):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    content_length = request.headers.get("content-length")
    if content_length and content_length.isdigit() and int(content_length) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail=f"File too large. Maximum size is {MAX_UPLOAD_BYTES // (1024 * 1024)} MB")

    file_bytes = await file.read()
    if len(file_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail=f"File too large. Maximum size is {MAX_UPLOAD_BYTES // (1024 * 1024)} MB")

    document_id = hashlib.sha256(file_bytes).hexdigest()

    store = get_store(tenant_id)
    if store.get("document_id") == document_id:
        return JSONResponse(
            content={"message": "Document already active", "status": JobStatus.completed},
            status_code=200
        )

    existing = await asyncio.to_thread(get_redis_metadata, document_id, tenant_id)
    if existing:
        store.update(existing)
        return JSONResponse(
            content={"message": "Document already processed", "status": JobStatus.completed},
            status_code=200
        )

    job_id = publish_upload_job(document_id, file.filename, file_bytes, tenant_id)

    return {
        "message": "Document accepted for processing",
        "job_id": job_id,
        "status": JobStatus.pending
    }


@router.get("/upload/status/{job_id}", dependencies=[Depends(verify_api_key), Depends(rate_limit(60, 60))])
async def get_upload_status(job_id: str):
    status = get_job_status(job_id)
    if not status:
        raise HTTPException(status_code=404, detail="Job not found")
    return status