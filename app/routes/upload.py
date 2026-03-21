from fastapi import APIRouter, UploadFile, HTTPException
from app.services.pdf import extract_text_from_pdf
from app.services.store import DOCUMENT_STORE

router = APIRouter()

@router.post("/upload")
async def upload_document(file: UploadFile):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    content, page_count = extract_text_from_pdf(await file.read())

    DOCUMENT_STORE["content"] = content
    DOCUMENT_STORE["filename"] = file.filename

    with open("output.txt", "wb") as out:
        out.write(content.encode("utf8"))

    return {"message": "Document uploaded successfully", "pages": page_count}
