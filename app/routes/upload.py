import hashlib, tempfile
from fastapi import APIRouter, UploadFile, HTTPException, Depends
from fastapi.responses import JSONResponse
from app.services.stream import publish_upload_job, get_job_status
from app.models.schemas import JobStatus
from app.dependencies import verify_api_key
from app.services.store import DOCUMENT_STORE
from app.services.cache import get_document_metadata as get_redis_metadata

router = APIRouter()

@router.post("/upload", dependencies=[Depends(verify_api_key)], status_code=202)
async def upload_document(file: UploadFile):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    file_bytes = await file.read()
    document_id = hashlib.sha256(file_bytes).hexdigest()

    if DOCUMENT_STORE.get("document_id") == document_id:
        return JSONResponse(
            content={"message": "Document already active", "status": JobStatus.completed},
            status_code=200
        )

    existing = get_redis_metadata(document_id)
    if existing:
        DOCUMENT_STORE.update(existing)
        return JSONResponse(
            content={"message": "Document already processed", "status": JobStatus.completed},
            status_code=200
        )

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(file_bytes)
        temp_path = tmp.name
    job_id = publish_upload_job(document_id, file.filename, temp_path)

    return {
        "message": "Document accepted for processing",
        "job_id": job_id,
        "status": JobStatus.pending
    }


@router.get("/upload/status/{job_id}", dependencies=[Depends(verify_api_key)])
async def get_upload_status(job_id: str):
    status = get_job_status(job_id)
    if not status:
        raise HTTPException(status_code=404, detail="Job not found")
    return status