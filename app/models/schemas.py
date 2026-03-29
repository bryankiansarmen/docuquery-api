from datetime import datetime, timezone
from pydantic import BaseModel, Field
from typing import Optional

class Question(BaseModel):
    message: str
    document_id: str
    session_id: Optional[str] = None

class DocumentMetadata(BaseModel):
    document_id: str
    file_name: str
    uploaded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    chunk_count: int
    page_count: int
    user_id: Optional[str] = None